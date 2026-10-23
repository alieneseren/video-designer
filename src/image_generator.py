import os
import torch
from pathlib import Path

# Patch transformers.utils.FLAX_WEIGHTS_NAME for compatibility with diffusers
try:
    import transformers.utils
    transformers.utils.FLAX_WEIGHTS_NAME = "model.msgpack"
except Exception as e:
    print(f"[IMAGEGEN-PATCH] utils patch exception: {e}")

# Patch transformers.CLIPFeatureExtractor for compatibility with diffusers
try:
    import transformers.utils.import_utils
    from transformers import CLIPImageProcessor
    transformers.utils.import_utils._LazyModule.CLIPFeatureExtractor = CLIPImageProcessor
except Exception as e:
    pass



class LocalImageGenerator:
    """Yerel Stable Diffusion (Lykon/dreamshaper-8) modeli ile yüksek kaliteli görseller üretir."""
    
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.pipe = None
        # Cihaz tespiti
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        print(f"[IMAGEGEN] Cihaz tespit edildi: {self.device}")

    def load_model(self):
        if self.pipe is not None:
            return
            
        from diffusers import StableDiffusionPipeline
        print("[IMAGEGEN] Stable Diffusion (Lykon/dreamshaper-8) modeli yükleniyor...")
        
        # Apple Silicon Mac'lerde float16 kullanımı hızı artırır ve RAM tüketimini azaltır,
        # ancak MPS altında float16 kullanımı NaN üretip siyah resimlere yol açabilir.
        # Bu yüzden MPS için float32 kullanıyoruz.
        torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        try:
            self.pipe = StableDiffusionPipeline.from_pretrained(
                "Lykon/dreamshaper-8",
                torch_dtype=torch_dtype,
                safety_checker=None,
                requires_safety_checker=False
            )
            self.pipe.to(self.device)
            
            # Mac MPS için attention slicing bellek kullanımını azaltır
            if self.device == "mps":
                self.pipe.enable_attention_slicing()
                
            print("[IMAGEGEN] Model başarıyla yüklendi.")
        except Exception as e:
            print(f"[IMAGEGEN] Model yükleme hatası: {e}")
            raise

    def generate(
        self,
        prompt: str,
        style_prompt: str = "",
        negative_prompt: str = "",
        seed: int = 42,
        width: int = 1080,
        height: int = 1920,
        steps: int = 20
    ):
        """
        Stable Diffusion kullanarak görsel üretir ve PIL Image nesnesi döndürür.
        """
        self.load_model()
        
        # Prompt birleştirme
        full_prompt = prompt
        if style_prompt:
            full_prompt = f"{prompt}, {style_prompt}"
            
        # Varsayılan negatif prompt (kaliteyi artırmak için)
        if not negative_prompt:
            negative_prompt = "ugly, deformed, disfigured, poor details, bad anatomy, bad hands, blurry, watermark, signature, cut off, duplicated"
            
        print(f"[IMAGEGEN] Görsel üretiliyor. Prompt: '{full_prompt[:80]}...' | Seed: {seed} | Cihaz: {self.device}")
        
        # Seed ile generator oluşturma (Görsel tutarlılığı sağlar)
        generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # SD 1.5 512x512 için eğitilmiştir. Shorts için 512x912, Landscape için 912x512 en iyi sonuçları verir.
        # Bu çözünürlüklerde üretip sonradan ölçeklemek deformasyonları engeller ve hızı artırır.
        if width < height:  # Shorts
            gen_w, gen_h = 512, 912
        else:  # Landscape
            gen_w, gen_h = 912, 512
            
        # Float16 MPS altında inference_mode veya autocast gerekir
        with torch.inference_mode():
            image = self.pipe(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=7.5,
                width=gen_w,
                height=gen_h,
                generator=generator
            ).images[0]
            
        return image
