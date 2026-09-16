# Local AI hardware upgrade notes

## Detected host

Collected on Windows 10 Pro, 2026-09-16:

- System: Dell Pro Max Tower T2, board `02RY37`, revision `A01`
- RAM: approximately 32 GB installed; Windows reports 4 memory slots and a 128 GB maximum
- GPU: one NVIDIA RTX 2000 Ada Generation
- GPU memory: 16,380 MiB reported by `nvidia-smi`
- Driver: 596.71
- Compute capability: 8.9
- GPU PCI bus: `00000000:01:00.0`
- Storage: Samsung PM9F1 SED 1 TB NVMe

## What this means

The RTX 2000 Ada is already being used successfully by Ollama at 100% GPU for the fast coding model. This is the best current path for interactive Colibri work. The larger Qwen3.6 Colibri model can remain a separate deep model, but it is CPU-bound on this host unless a CUDA build and compatible placement are added.

Windows inventory does not expose the tower's unused PCIe slot layout, power-supply wattage, auxiliary power connectors, or physical clearance reliably. Do not buy a second GPU based only on the current OS output.

## Upgrade checklist

1. Read the Dell Pro Max Tower T2 service manual for exact PCIe slot widths, bifurcation support, PSU wattage, and supported GPU power cables.
2. Open the case and photograph the motherboard slots, free rear brackets, PSU label, and current GPU clearance.
3. Check whether the second slot is electrically x16/x8 and whether it shares lanes with the NVMe or other devices.
4. Prefer a second matching or lower-power NVIDIA GPU only if the PSU and airflow support it.
5. For external GPUs, use a supported Thunderbolt/USB4 eGPU enclosure only if the tower exposes a suitable high-bandwidth port. Expect PCIe bandwidth loss compared with an internal card.
6. A separate GPU host connected over the LAN is often cleaner than a rack of consumer GPUs: run Ollama or Colibri on that host and point the local router/workbench at its OpenAI-compatible endpoint.

## Recommended next measurement

Use Dell's exact service documentation and a chassis inspection before any purchase. Then record:

- PSU model and wattage
- available PCIe slot positions and electrical widths
- GPU length/height clearance
- available 6/8-pin or 12VHPWR connectors
- idle/load temperatures and current GPU utilization

The software supports multiple configured model endpoints and future multi-instance workers, but physical multi-GPU support is constrained by the tower, PSU, PCIe topology, cooling, and the backend selected.
