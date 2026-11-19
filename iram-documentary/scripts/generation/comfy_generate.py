"""Queue SDXL + SDXL-Lightning images through a local ComfyUI server (CPU) and save each image with its
full API workflow, prompt, negative prompt, seed and settings (assets/images/<ID>.png + <ID>.json)."""
import argparse, json, time, uuid, urllib.request, pathlib, shutil, yaml, random
root = pathlib.Path(__file__).resolve().parents[2]
SERVER = 'http://127.0.0.1:8188'

def workflow(prompt, negative, seed, w, h, steps, lora, cfg):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "LoraLoader", "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": lora, "strength_model": 1.0, "strength_clip": 1.0}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": prompt}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": negative}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0],
              "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": 1.0}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "sdxl_vae.safetensors"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["7", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "iram"}},
    }

def workflow_i2i(prompt, negative, seed, image_name, denoise, steps, lora):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "LoraLoader", "inputs": {"model": ["1", 0], "clip": ["1", 1], "lora_name": lora, "strength_model": 1.0, "strength_clip": 1.0}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": prompt}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 1], "text": negative}},
        "5": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "sdxl_vae.safetensors"}},
        "10": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["7", 0]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["10", 0],
              "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler", "scheduler": "sgm_uniform", "denoise": denoise}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["7", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "iram_i2i"}},
    }

def post(path, data):
    req = urllib.request.Request(SERVER + path, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen(SERVER + path).read())

def run_one(aid, spec, styles, negs, out_dir, seed=None, w=1344, h=768, steps=8, variant=''):
    style = styles[spec['style']]; neg = negs['legend'] if spec['style'] == 'legend' else negs['default']
    prompt = f"{spec['prompt']}, {style}"
    seed = seed if seed is not None else random.Random(aid + variant).randint(1, 2**31)
    lora = 'sdxl_lightning_8step_lora.safetensors' if steps == 8 else 'sdxl_lightning_4step_lora.safetensors'
    if 'src' in spec:   # img2img over a Blender layout
        name = pathlib.Path(spec['src']).name; shutil.copy(root / spec['src'], pathlib.Path('/home/user/ComfyUI/input') / name)
        wf = workflow_i2i(prompt, neg, seed, name, spec['denoise'], steps, lora)
    else:
        wf = workflow(prompt, neg, seed, w, h, steps, lora, 1.0)
    t0 = time.time(); pid = post('/prompt', {'prompt': wf, 'client_id': str(uuid.uuid4())})['prompt_id']
    while True:
        hist = get(f'/history/{pid}')
        if pid in hist and hist[pid].get('outputs'): break
        if pid in hist and hist[pid].get('status', {}).get('status_str') == 'error': raise RuntimeError(json.dumps(hist[pid]['status'])[:800])
        time.sleep(2)
    img = hist[pid]['outputs']['9']['images'][0]
    src = pathlib.Path('/home/user/iram-work/comfy_out') / img.get('subfolder', '') / img['filename']
    name = f"{aid}{variant}"
    shutil.copy(src, out_dir / f"{name}.png")
    meta = {'id': aid, 'variant': variant, 'source_layout': spec.get('src'), 'denoise': spec.get('denoise', 1.0), 'prompt': prompt, 'negative_prompt': neg, 'seed': seed, 'width': w, 'height': h, 'steps': steps,
            'cfg': 1.0, 'sampler': 'euler', 'scheduler': 'sgm_uniform', 'checkpoint': 'stabilityai/stable-diffusion-xl-base-1.0 (sd_xl_base_1.0.safetensors)',
            'lora': f'ByteDance/SDXL-Lightning ({lora})', 'vae': 'madebyollin/sdxl-vae-fp16-fix', 'label': spec.get('label'),
            'compute_s': round(time.time() - t0, 1), 'comfyui_workflow_api': wf}
    (out_dir / f"{name}.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(json.dumps({'id': name, 'seed': seed, 'compute_s': meta['compute_s']}), flush=True)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('ids', nargs='*'); ap.add_argument('--variants', type=int, default=1)
    ap.add_argument('--steps', type=int, default=8); ap.add_argument('--force', action='store_true'); a = ap.parse_args()
    cfg = yaml.safe_load(open(root / 'storyboard/assets.yaml', encoding='utf-8'))
    out = root / 'assets/images'; out.mkdir(parents=True, exist_ok=True)
    specs = {**cfg['ai'], **cfg.get('img2img', {})}
    ids = a.ids or list(specs.keys())
    for aid in ids:
        for v in range(a.variants):
            var = '' if a.variants == 1 else f'_v{v+1}'
            if (out / f"{aid}{var}.png").exists() and not a.force: continue
            try:
                run_one(aid, specs[aid], cfg['style'], cfg['negative'], out, steps=a.steps, variant=var)
            except Exception as e:
                print(json.dumps({'id': aid, 'error': str(e)[:300]}), flush=True)
    print('GENERATION_DONE', flush=True)
