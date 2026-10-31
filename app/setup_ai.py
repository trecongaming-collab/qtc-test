"""Explicit model installation. Downloads public weights, never reads user media."""
import json
from .vision import MODEL_DIR, WEIGHTS


def main():
    import torch
    from torchvision.models import ResNet18_Weights
    from torchvision.models.detection import SSDLite320_MobileNet_V3_Large_Weights
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    torch.hub.set_dir(str(MODEL_DIR))
    manifest=[]
    for name, weights in [('resnet18',ResNet18_Weights.IMAGENET1K_V1),('ssdlite',SSDLite320_MobileNet_V3_Large_Weights.COCO_V1)]:
        print(f'Downloading public pretrained model: {name}',flush=True)
        weights.get_state_dict(progress=True,check_hash=True)
        manifest.append({'name':name,'file':WEIGHTS[name],'url':weights.url})
    (MODEL_DIR/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    from .vision import get_vision
    vision=get_vision()
    print(json.dumps({'ready':True,'sha256':vision.fingerprints}))

if __name__=='__main__': main()
