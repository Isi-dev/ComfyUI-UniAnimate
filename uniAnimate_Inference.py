import torch

from .utils.config import Config
from .tools.inferences import inference_unianimate_entrance
from .tools.inferences import inference_unianimate_long_entrance
from . import run_align_pose
from . import run_align_posev2

# from tools import *



class UniAnimateImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 11, "min": 0, "max": 1000000000000, "step": 1}),
                "steps": ("INT", {"default": 30, "min": 25, "max": 50, "step": 1}),
                "useFirstFrame": ("BOOLEAN", { "default": False }),
                "reference_image": ("IMAGE",),  # single image
                "ref_pose": ("IMAGE",),  # single image
                "pose_sequence": ("IMAGE",),   # Batch of pose images
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 8, "step": 1}),
                "max_frames": ("INT", {"default": 32, "min": 1, "max": 64, "step": 1}),
                "resolution_x": ("INT", {"default": 512, "min": 512, "max": 768, "step": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, seed, steps, useFirstFrame, reference_image, ref_pose, pose_sequence, frame_interval, max_frames, resolution_x):
        cfg_update = Config('configs/UniAnimate_infer.yaml', load=True)
        resolution_y = 768
        if resolution_x == 768:
            resolution_y = 1216
        resolution = [resolution_x, resolution_y]
        print("Ready for inference.")
        
        # print(f"image is: {reference_image}")
        
        frames = inference_unianimate_entrance(seed, steps, useFirstFrame, reference_image, ref_pose, pose_sequence, frame_interval, max_frames, resolution, cfg_update=cfg_update.cfg_dict)
        mask_template = torch.zeros((1, resolution_y, resolution_x), dtype=torch.float32)
        masks = [mask_template.clone() for _ in range(len(pose_sequence))]
        masks = torch.cat(masks, dim=0)
        return (frames, masks)

class Gen_align_pose:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_image": ("IMAGE",),  # single image
                "video": ("IMAGE",),   # video
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, reference_image, video):    
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"CUDNN version: {torch.backends.cudnn.version()}")
            print(f"Device name: {torch.cuda.get_device_name(0)}")
        else:
            print("CUDA is not available")
        poses, refPose = run_align_pose.mp_main(reference_image, video)
        return (refPose, poses)
    


class UniAnimateImageLong:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 7, "min": 0, "max": 1000000000000, "step": 1}),
                "steps": ("INT", {"default": 30, "min": 20, "max": 50, "step": 1}),
                "useFirstFrame": ("BOOLEAN", { "default": False }),
                "dontAlignPose": ("BOOLEAN", { "default": False }),
                "image": ("IMAGE",),  # single image
                "video": ("IMAGE",),   # Batch of pose images
                "frame_interval": ("INT", {"default": 1, "min": 1, "max": 16, "step": 1}),
                "context_size": ("INT", {"default": 32, "min": 16, "max": 64, "step": 16}),
                "context_stride": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "context_overlap": ("INT", {"default": 8, "min": 4, "max": 16, "step": 4}),
                "max_frames": ("INT", {"default": 1024000, "min": 16, "max": 1024000, "step": 1}),
                "resolution_x": ("INT", {"default": 512, "min": 512, "max": 768, "step": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("video", "poses")
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, seed, steps, useFirstFrame, dontAlignPose, image, video, frame_interval, context_size, context_stride, context_overlap, max_frames, resolution_x):
        cfg_update = Config('configs/UniAnimate_infer_long.yaml', load=True)
        resolution_y = 768
        if resolution_x == 768:
            resolution_y = 1216
        resolution = [resolution_x, resolution_y]

        context_size = context_size
        context_overlap = context_overlap
        max_frames = max_frames
        if context_size == context_overlap:
            context_overlap = 8
            print("context_size equal to context_overlap; context_overlap changed to default.")
        
        if context_size > max_frames or context_size > len(video) :
            context_size = 32
            print("context_size greater than max_frames; context_size changed to default.")

        if max_frames < 32 or len(video) < 32:
            context_size = 16
            context_overlap = 4
            print("Video frames less than 32; context_size changed to 16 and context_overlap changed to 4.")

        pose_sequence, refPose = run_align_posev2.mp_main(dontAlignPose, image, video)

        print("Ready for inference.")
        
        frames = inference_unianimate_long_entrance(seed, steps, useFirstFrame, image, refPose, pose_sequence, frame_interval, context_size, context_stride, context_overlap, max_frames, resolution, cfg_update=cfg_update.cfg_dict)

        return (frames, pose_sequence)
    


class ReposeImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 11, "min": 0, "max": 1000000000000, "step": 1}),
                "steps": ("INT", {"default": 30, "min": 20, "max": 50, "step": 1}),
                "dontAlignPose": ("BOOLEAN", { "default": False }),
                "image": ("IMAGE",),
                "pose": ("IMAGE",), 
                "resolution_x": ("INT", {"default": 512, "min": 512, "max": 768, "step": 256}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("newPose", "pose")
    FUNCTION = "process"
    CATEGORY = "image"

    def process(self, seed, steps, dontAlignPose, image, pose, resolution_x):
        cfg_update = Config('configs/UniAnimate_infer.yaml', load=True)
        resolution_y = 768
        if resolution_x == 768:
            resolution_y = 1216
        resolution = [resolution_x, resolution_y]
        
        pose_i, refPose = run_align_posev2.mp_main(dontAlignPose, image, pose)

        print("Ready for inference.")
        frame = inference_unianimate_entrance(seed, steps, False, image, refPose, pose_i, 1, 1, resolution, cfg_update=cfg_update.cfg_dict)
        # mask_template = torch.zeros((1, resolution_y, resolution_x), dtype=torch.float32)
        # masks = [mask_template.clone() for _ in range(len(pose_i))]
        # masks = torch.cat(masks, dim=0)

        return (frame, pose_i)



NODE_CLASS_MAPPINGS = {
    "UniAnimateImage" : UniAnimateImage,
    "Gen_align_pose" : Gen_align_pose,
    "UniAnimateImageLong" : UniAnimateImageLong,
    "ReposeImage" : ReposeImage,
    
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UniAnimateImage" :"Animate image with UniAnimate",
    "Gen_align_pose" :"Align & Generate poses for UniAnimate",
    "UniAnimateImageLong" :"Animate image with UniAnimate_Long",
    "ReposeImage" :"Repose image with UniAnimate",
    
}
