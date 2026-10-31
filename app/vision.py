"""Real pretrained local inference. Runtime never downloads models or uploads media."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import threading

MODEL_DIR = Path(os.environ.get('QTC_MODEL_DIR', Path(__file__).resolve().parent.parent/'work'/'models')).resolve()
WEIGHTS = {
    'resnet18': 'resnet18-f37072fd.pth',
    'ssdlite': 'ssdlite320_mobilenet_v3_large_coco-a79551df.pth',
}
SCENES = {
    'coast': {'seashore','sandbar','promontory','coral reef','breakwater','pier','lakeside','dock','catamaran','trimaran','yawl','schooner','canoe'},
    'nature': {'alp','valley','volcano','cliff','geyser','lakeside','rapeseed','daisy','pot','acorn','mushroom','hen-of-the-woods','earthstar','bolete'},
    'architecture': {'palace','castle','monastery','church','mosque','stupa','dome','bell cote','triumphal arch','viaduct','suspension bridge','boathouse','fountain','patio'},
    'food': {'plate','hot pot','pizza','cheeseburger','ice cream','guacamole','consomme','espresso','cup','red wine','restaurant'},
    'transport': {'airliner','airship','speedboat','motor scooter','mountain bike','sports car','convertible','jeep','minibus','passenger car','bullet train','aircraft carrier'},
    'interior': {'library','bookshop','barbershop','bakery','grocery store','home theater','living room','bedroom','dining table','studio couch'},
}


def readiness():
    dependencies = all(importlib.util.find_spec(m) is not None for m in ('torch','torchvision','cv2','scipy'))
    missing = [name for name,file in WEIGHTS.items() if not (MODEL_DIR/'checkpoints'/file).is_file()]
    return {'ready': dependencies and not missing, 'dependencies': dependencies,
            'missing_models': missing, 'backend':'local-pytorch', 'media_upload_to_third_party':False,
            'models':['ResNet18 ImageNet-1K','SSDLite320 MobileNetV3 COCO'],
            'message':'AI cục bộ sẵn sàng' if dependencies and not missing else 'Chạy setup-ai-windows.cmd để cài AI và tải mô hình trước.'}


class LocalVision:
    def __init__(self):
        status = readiness()
        if not status['ready']:
            raise ValueError(status['message'])
        import torch
        from torchvision.models import resnet18, ResNet18_Weights
        from torchvision.models.detection import ssdlite320_mobilenet_v3_large, SSDLite320_MobileNet_V3_Large_Weights
        self.torch = torch
        torch.set_num_threads(max(1,min(4,int(os.environ.get('QTC_AI_THREADS','2')))))
        self.classifier = resnet18(weights=None).eval()
        self.detector = ssdlite320_mobilenet_v3_large(weights=None,weights_backbone=None).eval()
        self.classifier.load_state_dict(torch.load(MODEL_DIR/'checkpoints'/WEIGHTS['resnet18'],map_location='cpu',weights_only=True))
        self.detector.load_state_dict(torch.load(MODEL_DIR/'checkpoints'/WEIGHTS['ssdlite'],map_location='cpu',weights_only=True))
        self.features = torch.nn.Sequential(*list(self.classifier.children())[:-1]).eval()
        self.transform = ResNet18_Weights.IMAGENET1K_V1.transforms()
        self.labels = ResNet18_Weights.IMAGENET1K_V1.meta['categories']
        self.object_labels = SSDLite320_MobileNet_V3_Large_Weights.COCO_V1.meta['categories']
        self.fingerprints = {k:hashlib.sha256((MODEL_DIR/'checkpoints'/f).read_bytes()).hexdigest() for k,f in WEIGHTS.items()}

    def infer(self, rgb):
        import numpy as np
        from PIL import Image
        from torchvision.transforms.functional import to_tensor
        t = self.torch
        image = Image.fromarray(rgb)
        with t.inference_mode():
            feature = self.features(self.transform(image).unsqueeze(0)).flatten(1)
            probabilities = self.classifier.fc(feature).softmax(1)[0]
            values, indices = probabilities.topk(5)
            prediction = self.detector([to_tensor(image)])[0]
        objects=[]
        h,w=rgb.shape[:2]
        for box,label,confidence in zip(prediction['boxes'],prediction['labels'],prediction['scores']):
            if float(confidence)<.45: continue
            objects.append({'label':self.object_labels[int(label)],'confidence':round(float(confidence),4),
                            'box':[round(float(box[0])/w,4),round(float(box[1])/h,4),round(float(box[2])/w,4),round(float(box[3])/h,4)]})
        evidence=[{'label':self.labels[int(i)],'confidence':round(float(p),4)} for p,i in zip(values,indices)]
        groups={group:round(sum(float(probabilities[i]) for i,label in enumerate(self.labels) if label in labels),4) for group,labels in SCENES.items()}
        if any(o['label']=='person' for o in objects): groups['people']=max(o['confidence'] for o in objects if o['label']=='person')
        best=max(groups,key=groups.get)
        tag=best if groups[best]>=.12 else 'unknown'
        vector=feature[0].numpy(); vector=vector/max(float(np.linalg.norm(vector)),1e-8)
        return {'tag':tag,'scene_scores':groups,'labels':evidence,'objects':objects,'embedding':vector.tolist(),
                'semantic_confidence':round(float(max(groups.values())),4),'inference':'pretrained-local',
                'aesthetic_model':False}


_instance=None
_lock=threading.Lock()

def get_vision():
    global _instance
    with _lock:
        if _instance is None: _instance=LocalVision()
    return _instance
