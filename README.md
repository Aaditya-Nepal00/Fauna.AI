# Fauna.AI: Advanced Wildlife Intelligence for Nepal

Fauna.AI is a modular computer vision system designed to automate the monitoring of high-value species within Nepal's protected areas. The platform addresses the critical bottleneck in conservation research: the manual processing of hundreds of thousands of motion-triggered camera trap images. 

By implementing a three-layer intelligence pipeline, Fauna.AI allows biologists to move from data sorting to ecological analysis, focusing resources on the protection of flagship species like the Bengal Tiger (*Panthera tigris*) and the Greater One-horned Rhino (*Rhinoceros unicornis*).

## Intelligence Pipeline

The system operates through three sequential processing layers, each designed to refine the data stream and extract actionable biological insights.

### Layer 01: FrameGuard
Camera traps frequently trigger due to wind-blown vegetation or shifting shadows, leading to a high volume of 'blank' frames. FrameGuard utilizes a YOLOv8-based detection model to scan incoming footage for any animal presence. By filtering out these empty frames at the edge or ingestion point, the system reduces manual review effort by approximately 70%, ensuring that only frames containing relevant biological data proceed to classification.

### Layer 02: SpeciesID
Filtered frames are passed to a fine-tuned EfficientNet-B4 classifier. This model is specifically trained on a dataset of Nepal-specific fauna. It distinguishes between species of high conservation priority and more common species. This layer provides the primary identification necessary for population density estimates and individual tracking.

### Layer 03: PulseScan
PulseScan performs temporal behavior analysis across sequences of images. Instead of treating images as isolated data points, it analyzes the frequency, duration, and timing of species presence. This layer is designed to identify behavioral anomalies—such as shifts in nocturnal activity or unusual presence near human settlements—that may indicate environmental stressors or poaching threats.

## Project Structure

* backend/: FastAPI application handling model inference and data management.
* frontend/: React-based dashboard for biologists to review detections and visualize population trends.
* models/: Storage for serialized model weights and architecture configurations.
* processing/: Implementation of the FrameGuard, SpeciesID, and PulseScan layers.
* data/: Structured storage for raw ingestion, processed results, and the review queue.
* docs/: Technical architecture diagrams and onboarding guides for field biologists.

## Conservation Impact

In the context of Nepal's diverse landscapes—from the subtropical Terai to the high Himalayas—accurate wildlife data is the foundation of effective policy. Fauna.AI minimizes the lag between field data collection and conservation action, providing the Terai Arc Landscape (TAL) and other critical corridors with a state-of-the-art monitoring infrastructure.
