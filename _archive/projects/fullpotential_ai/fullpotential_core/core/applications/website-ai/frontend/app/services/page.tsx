import Link from "next/link";

type ServiceSummary = {
  slug: string;
  name: string;
  status: "online" | "building" | "pending";
  lead: string;
  description: string;
  highlight: string;
};

const services: ServiceSummary[] = [
  {
    slug: "whaletrack",
    name: "WhaleTrack",
    status: "online",
    lead: "Markets Core",
    description:
      "Autonomous liquidity radar that follows whale intention → magnet. Live on port 8600 with God Mode telemetry.",
    highlight: "Port 8600 · Deployed",
  },
  {
    slug: "god-mode",
    name: "God Mode",
    status: "online",
    lead: "Conscious Kernel",
    description:
      "System map + live mission board. Keeps every droplet aligned to the Constitution.",
    highlight: "Port 8300 · System Map",
  },
  {
    slug: "strategic-intelligence",
    name: "Strategic Intelligence",
    status: "building",
    lead: "Brain Team",
    description:
      "Autonomous prioritization engine. Currently ingesting dashboards + treasury feeds.",
    highlight: "Port 8500 · In flight",
  },
];

const statusPill: Record<ServiceSummary["status"], string> = {
  online: "Online",
  building: "Building",
  pending: "Pending",
};

export default function ServicesPage() {
  return (
    <main className="services-page">
      <div className="panel">
        <section className="services-hero">
          <p className="status-pill">Live / Services</p>
          <h1>fullpotential.ai/services</h1>
          <p>
            Every service is a living organ — UDC compliant, observable, and
            bound to the Constitution. Explore the catalog below and deep dive
            into the WhaleTrack trading brain.
          </p>
        </section>

        <div className="services-grid">
          {services.map((service) => (
            <Link
              key={service.slug}
              href={`/services/${service.slug}`}
              className="service-card"
            >
              <div className="status">
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "999px",
                    background:
                      service.status === "online" ? "#22c55e" : "#fbbf24",
                  }}
                />
                {statusPill[service.status]}
              </div>
              <h3>{service.name}</h3>
              <p style={{ margin: 0 }}>{service.description}</p>
              <p style={{ margin: 0, color: "#94a3b8" }}>
                <strong>Lead:</strong> {service.lead}
              </p>
              <p style={{ margin: 0, color: "#cbd5f5" }}>{service.highlight}</p>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}

