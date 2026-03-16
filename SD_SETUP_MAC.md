# How to Install Stable Diffusion (Unrestricted) on Mac M2

This guide sets up **Automatic1111**, the industry-standard interface for running Stable Diffusion. It runs locally on your Mac, costs nothing per image, and has **NO safety filters**.

## 1. Install Prerequisites (Terminal)
Open your Terminal and run these commands one by one:

```bash
# 1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Required Tools
brew install cmake protobuf rust python@3.10 git wget
```

## 2. Clone the Repository
We will download the Automatic1111 WebUI to your home folder.

```bash
cd ~
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui
```

## 3. Run It
This first run will take a while (it downloads the default model ~4GB).

```bash
./webui.sh
```

**Wait until you see:**
`Running on local URL:  http://127.0.0.1:7860`

Once you see that, the server is live!

---

## 4. Enable API Mode (CRITICAL)
For our App to talk to Stable Diffusion, we need to restart it with the API flag enabled.

1.  Stop the server (Control+C in terminal).
2.  Edit the run script or just run it specifically like this:
```bash
./webui.sh --api --listen 
```
*Tip: `--api` allows our app to control it. `--listen` makes it accessible.*

## 5. Download Custom Models (NSFW/Realism)
The default model is basic. For high-quality, unfiltered realism, download a checkpoint like **"CyberRealistic"** or **"Juggernaut XL"** from [Civitai.com](https://civitai.com).

1.  Download the `.safetensors` file.
2.  Move it to: `~/stable-diffusion-webui/models/Stable-diffusion/`
3.  Refresh the list in the WebUI (top left) and select it.

---

## Troubleshooting
*   **"Torch not compiled with CUDA"**: Normal on Mac. The script usually detects M2 and uses "MPS" (Metal Performance Shaders) automatically.
*   **Slow**: On M2, it should take 10-20 seconds per image.
