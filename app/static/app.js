const $=s=>document.querySelector(s);
let active=null,lastId=null,config=null,lastReport=null;
const names={opening:'Mở đầu',development:'Phát triển',climax:'Cao trào',ending:'Kết thúc'};
function busy(value){$('#build').disabled=value||!config?.ai.ready;$('#regenerate').disabled=value}
function error(message){$('#error').textContent=message;busy(false)}
function files(){
  $('#files').replaceChildren();
  for(const file of $('#videos').files){const li=document.createElement('li');li.textContent=`${file.name} · ${(file.size/1024/1024).toFixed(1)} MB`;$('#files').append(li)}
}
$('#videos').onchange=files;
$('#duration').oninput=e=>$('#seconds').textContent=`${e.target.value} giây`;
$('#music').onchange=()=>$('#music-name').textContent=$('#music').files[0]?.name||'Chọn bản nhạc của bạn';
for(const type of ['dragenter','dragover'])$('#drop').addEventListener(type,e=>{e.preventDefault();$('#drop').classList.add('over')});
for(const type of ['dragleave','drop'])$('#drop').addEventListener(type,e=>{e.preventDefault();$('#drop').classList.remove('over')});
$('#drop').addEventListener('drop',e=>{$('#videos').files=e.dataTransfer.files;files()});
function start(id){active=id;sessionStorage.setItem('qtc-job',id);$('#error').textContent='';$('#warnings').textContent='';$('#progress-area').hidden=false;$('#evidence').hidden=true;busy(true);poll(id)}
async function showResult(id,state){
  lastId=id;sessionStorage.setItem('qtc-last',id);sessionStorage.removeItem('qtc-job');
  $('#preview').src=`/api/jobs/${id}/video`;$('#preview').hidden=false;$('#placeholder').hidden=true;
  $('#download').href=`/api/jobs/${id}/video?download=true`;$('#report').href=`/api/jobs/${id}/report`;
  for(const element of ['#download','#report','#regenerate','#inspect'])$(element).hidden=false;
  $('#version').textContent=`BẢN ${(state.summary?.variant||0)+1}`;
  try{
    const response=await fetch(`/api/jobs/${id}/report`);if(!response.ok)throw Error('Không đọc được báo cáo');
    lastReport=await response.json();const out=lastReport.output;
    if(lastReport.style)$('#style').value=lastReport.style;
    $('#duration').value=Math.round(out.duration);$('#seconds').textContent=`${Math.round(out.duration)} giây`;
    $('#resolution').value=Math.min(out.width,out.height)>=2160?'4k':'1080p';
    $('#aspect').value=out.width>out.height?'16:9':'9:16';
    $('#phone').classList.toggle('is-landscape',out.width>out.height);
    $('#phone').style.aspectRatio=`${out.width}/${out.height}`;
    $('#story').replaceChildren();
    for(const chapter of lastReport.chapters||[]){const span=document.createElement('span');span.textContent=`${names[chapter.name]||chapter.name} · ${chapter.start.toFixed(1)}s`;$('#story').append(span)}
    $('#story').hidden=false;
    $('#warnings').textContent=(lastReport.warnings||[]).join(' ');
  }catch(e){$('#warnings').textContent=e.message}
  busy(false);
}
async function poll(id){
  try{
    const response=await fetch(`/api/jobs/${id}`);if(!response.ok)throw Error('Không đọc được trạng thái tác vụ');
    const state=await response.json();$('#bar').style.width=`${state.progress}%`;$('#message').textContent=state.message;
    if(state.status==='done'){await showResult(id,state);return}
    if(state.status==='error'){sessionStorage.removeItem('qtc-job');error(state.message);return}
    setTimeout(()=>poll(id),1600);
  }catch(e){error(`${e.message}. Tải lại trang để thử kết nối lại.`)}
}
$('#editor').onsubmit=e=>{
  e.preventDefault();const videos=[...$('#videos').files],music=$('#music').files[0];
  if(!config?.ai.ready)return error('AI chưa sẵn sàng. Chạy setup-ai-windows.cmd và khởi động lại ứng dụng.');
  if(videos.length<5||videos.length>20)return error('Vui lòng chọn 5–20 video.');
  if(!music)return error('Vui lòng chọn nhạc nền.');
  const inputs=[...videos,music],total=inputs.reduce((n,f)=>n+f.size,0);
  if(inputs.some(f=>f.size>config.max_file_bytes)||total>config.max_total_bytes)return error('Dung lượng vượt giới hạn hiển thị của máy chủ.');
  if(total*2+512*1024**2>config.disk_free_bytes)return error('Ổ đĩa có thể không đủ chỗ cho upload và bản dựng. Dọn thư mục work hoặc đổi ổ dữ liệu.');
  busy(true);$('#error').textContent='';$('#progress-area').hidden=false;$('#bar').style.width='0%';$('#message').textContent='Đang tải nguồn lên máy chạy ứng dụng…';
  const data=new FormData();videos.forEach(f=>data.append('videos',f));data.append('music',music);data.append('mode','ai');
  for(const field of ['duration','style','resolution','aspect'])data.append(field,$(`#${field}`).value);
  for(const field of ['ramp','nature'])data.append(field,$(`#${field}`).checked);
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/jobs');
  xhr.upload.onprogress=e=>{if(e.lengthComputable)$('#message').textContent=`Đang tải nguồn… ${Math.round(e.loaded/e.total*100)}%`};
  xhr.onerror=()=>error('Mất kết nối khi tải. Vui lòng thử lại.');
  xhr.onload=()=>{try{const result=JSON.parse(xhr.responseText);if(xhr.status!==202)throw Error(typeof result.detail==='string'?result.detail:'Dữ liệu không hợp lệ');start(result.id)}catch(e){error(e.message)}};
  xhr.send(data);
};
$('#regenerate').onclick=async()=>{
  if(!lastId)return;busy(true);$('#error').textContent='';
  try{const response=await fetch(`/api/jobs/${lastId}/regenerate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({style:$('#style').value,resolution:$('#resolution').value,aspect:$('#aspect').value})});const result=await response.json();if(!response.ok)throw Error(result.detail||'Không tạo được phiên bản');start(result.id)}catch(e){error(e.message)}
};
$('#inspect').onclick=()=>{
  const box=$('#evidence');box.replaceChildren();
  for(const shot of (lastReport?.selected||[]).slice(0,12)){
    const p=document.createElement('p');const labels=shot.labels?.[1]||[];
    const objects=[...new Set((shot.objects||[]).map(o=>o.label))];
    p.textContent=`${shot.timeline.toFixed(1)}s · ${names[shot.phase]||''} · nguồn ${shot.source+1} tại ${shot.start.toFixed(1)}s. ${shot.reason||''}. AI: ${shot.tag||'không chắc'}; đối tượng ${objects.join(', ')||'chưa chắc'}; ${labels.slice(0,2).map(l=>`${l.label} ${(l.confidence*100).toFixed(0)}%`).join(', ')}. Chất lượng đo: ${(shot.quality_score*100).toFixed(0)}/100.`;
    box.append(p);
  }
  box.hidden=!box.hidden;
};
(async()=>{
  try{const response=await fetch('/api/config');if(!response.ok)throw Error('Không đọc được cấu hình máy chủ');config=await response.json();
    $('#ai-state').textContent=config.ai.ready?'AI cục bộ sẵn sàng · ResNet18 + SSDLite · video không rời máy chạy ứng dụng':config.ai.message;
    $('#ai-state').classList.toggle('missing',!config.ai.ready);
    $('#limits').textContent=`Tối đa ${Math.round(config.max_file_bytes/1024**3)} GB/tệp · ${Math.round(config.max_total_bytes/1024**3)} GB/tác vụ · cần đủ dung lượng trống`;
    active=sessionStorage.getItem('qtc-job');lastId=sessionStorage.getItem('qtc-last');
    if(active){$('#progress-area').hidden=false;busy(true);poll(active)}else{busy(false);if(lastId){$('#progress-area').hidden=false;poll(lastId)}}
  }catch(e){$('#ai-state').textContent=e.message;error(e.message)}
})();
