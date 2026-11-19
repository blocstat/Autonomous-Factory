# THE AUTONOMOUS FACTORY COMPANY
## Master Project Context — November 18, 2026

**Founder:** Rami Saintus  
**Location:** Québec, Canada  
**Status:** Early architecture and prototype planning; physical implementation not confirmed.

## Mission
Build an engineering and technology company that progressively designs, builds, deploys and operates intelligent autonomous factories on Earth, with eventual research into space-adapted manufacturing. Start with a commercially valuable industrial monitoring product, validate it, earn customer trust and expand capabilities incrementally.

## Founder and constraints
Engineering background in electrical systems, telecommunications, electronics, embedded systems, infrastructure and entrepreneurship. Developing expertise in AI engineering, industrial automation, robotics and manufacturing. Current resources: MacBook Pro 13-inch (2021), 16 GB RAM; Galaxy S22 Ultra; approximately 2 focused hours per day / 14 hours per week; current employment; limited initial capital. Do not assume a laboratory, purchased hardware, machinery, paying customers or completed experiments.

## Three technology layers
1. **AI in Things:** Sensors, microcontrollers, ESP32-S3, embedded C/C++, FreeRTOS, signal processing, edge inference and anomaly detection at the machine level.
2. **AI of Things (AIoT):** Connected devices, MQTT, gateways, time-series storage, device management, fleet analytics, predictive maintenance research and digital twin foundations.
3. **Autonomous Engineering:** Long-term AI-assisted CAD/CAE, simulation, robotics, manufacturing process planning, factory layout, production orchestration and human-supervised autonomous operations.

The immediate focus is Layer 1, with just enough Layer 2 to demonstrate an end-to-end product. Layer 3 is a long-term roadmap, not an MVP deliverable.

## Initial product hypothesis
A modular ESP32-S3-based industrial machine-monitoring and anomaly-detection system, potentially adaptable to motors, pumps, fans, compressors, gearboxes and rotating equipment. Initial observations may include vibration and temperature; electrical current is optional and requires a safe interface. Aim to establish baselines and detect deviations, not to claim universal fault diagnosis or predictive maintenance.

### MVP requirements
- Safe sensor mounting, signal conditioning and power architecture.
- Reliable timestamped sampling, buffering, logging and communication.
- Initial USB serial transport; Wi-Fi/MQTT only when justified.
- Signal processing (filtering, statistical features, FFT/spectral features).
- Python analysis, time-series storage and basic visualization.
- Baseline and deviation detection with explicit false-positive analysis.
- Reproducible tests, documented limitations and evidence artifacts.

### Proposed pipeline
Machine → Sensors → Signal conditioning → ESP32-S3 → Edge processing → Transport → Backend → Storage → Analytics → Dashboard → Human operator.

### Candidate stack (not mandatory)
ESP-IDF, C/C++, FreeRTOS, Git; Python, NumPy, SciPy, Pandas, Matplotlib, scikit-learn; FastAPI and SQLite initially if backend is necessary; MQTT and Grafana when justified. Prefer explainable signal processing and lightweight baselines before deep learning.

## Engineering considerations
Select sensors based on required frequency bandwidth, mounting, sensitivity, noise, sampling and aliasing. Assess ADC/interface quality, EMI, grounding, cable shielding, isolation, power, environmental protection and serviceability. A development board is not an industrial-certified product.

Do not connect experimental hardware directly to mains or safety-critical controls. Prefer safe, non-invasive or isolated measurements and appropriate professional review. Consider applicable Québec/OIQ requirements and relevant standards for the actual use case. No AI-generated design is professionally approved without human verification.

## Competitive and commercial research
Benchmark Schaeffler OPTIME objectively. Potential differentiation hypotheses: modularity, interoperability, transparent data access, customization, accessible deployment for SMEs and future digital twin integration. Do not claim superiority without evidence.

Investigate small/medium manufacturers, maintenance teams, OEMs, integrators and industrial service companies. Test problem severity, current alternatives, decision-maker, willingness to pay and pilot requirements. Possible models: hardware + subscription, monitoring-as-a-service, integration services and OEM partnerships. None is validated yet.

## Phased roadmap
- **0 Foundation:** Development environment, repository, documentation, architecture, BOM, safety review.
- **1 Acquisition:** First sensor integration, reliable timestamped data, computer streaming and visualization.
- **2 Detection:** Filtering, FFT/features, baseline, deviation scoring and repeatability tests.
- **3 Platform:** Device registry, telemetry, storage, dashboard, basic alerts.
- **4 Field validation:** Customer discovery, safe pilot, reliability and economics.
- **5 Commercial MVP:** Hardening, cybersecurity, installation, support, pricing and compliance.
- **6 AIoT expansion:** Multi-site fleet analytics, industrial integrations, digital twins.
- **7 Autonomous engineering:** Robotics, simulation and factory orchestration research.

## Collaboration model
- **Founder:** Owns priorities, decisions, budget, engineering sign-off and customer relationships.
- **ChatGPT:** Strategy, roadmap, sprint planning, architecture reviews and progress reconciliation.
- **Claude:** Research, systems engineering, tradeoffs, design criticism and documentation.
- **Claude Code:** Repository-level implementation, tests, debugging and scoped automation.
- **Cursor:** Primary IDE for firmware, Python, backend, dashboards and code review.
- **Git:** Versioned source of truth for code and engineering artifacts.
- **Notion:** Company headquarters for milestones, decisions, weekly execution, budgets and customer discovery.

## Working rules for every AI assistant
1. Focus on one verifiable weekly outcome within ~14 hours.
2. State facts, assumptions, recommendations and unknowns separately.
3. Do not invent hardware purchases, tests, customers, results or progress.
4. Propose the smallest technically defensible implementation.
5. Explain key engineering decisions and tradeoffs.
6. Include tests, acceptance criteria, risks and evidence artifacts.
7. Avoid premature infrastructure, dependencies and spending.
8. Label synthetic data explicitly; never pass it off as measured data.
9. Request approval before major architecture changes, costs or hazardous actions.
10. Keep documentation and decisions synchronized with implementation.

## Status as of November 18, 2026
**Defined in discussion:** company vision, three layers, ESP32-S3 monitoring concept, multi-machine aspiration, competitor benchmark, 14-hour schedule and tool workflow.

**Not yet evidenced as complete:** purchased hardware, wiring, firmware, calibration, measurements, validated anomaly model, customer interviews, pilot or revenue.

## First assignment
Review the MVP architecture; identify high-risk assumptions; propose a safe, hardware-independent first experiment; recommend a minimal repository and development environment; and produce a 14-hour sprint with explicit acceptance criteria. Do not build the full platform.

**Principle:** Build small. Validate rigorously. Learn continuously. Commercialize deliberately. Scale toward autonomous manufacturing.
