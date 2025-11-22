export interface DropletData {
  id: number;
  name: string;
  repo: string;
  purpose: string;
  steward: string;
  status: string;
  liveEndpoint?: string;
  healthcheck?: string;
  upstreamDependencies: string[];
  relatedDroplets: string[];
  currentSprint?: string;
  techStack: string[];
  complianceScore?: string;
}

export function parseReadme(content: string, repo: string): DropletData | null {
  try {
    const idMatch = content.match(/Droplet #(\d+)/i);
    const nameMatch = content.match(/# Droplet #\d+:\s*(.+)/i);
    const purposeMatch = content.match(/\*\*Purpose:\*\*\s*(.+)/i);
    const stewardMatch = content.match(/\*\*Steward:\*\*\s*(.+)/i);
    const statusMatch = content.match(/\*\*Status:\*\*\s*(.+)/i);
    const endpointMatch = content.match(/\*\*Live Endpoint:\*\*\s*(.+)/i);
    const healthMatch = content.match(/\*\*Healthcheck:\*\*\s*(.+)/i);
    const complianceMatch = content.match(/\*\*Compliance Score:\*\*\s*(.+)/i);

    const upstreamSection = content.match(/\*\*Upstream Dependencies:\*\*\s*([\s\S]*?)(?=\n\n|\*\*Downstream)/i);
    const upstreamDeps = upstreamSection 
      ? upstreamSection[1].match(/#(\d+)\s+([^(\n]+)/g)?.map(d => d.trim()) || []
      : [];

    const relatedSection = content.match(/\*\*Related Droplets:\*\*\s*([\s\S]*?)(?=\n\n|---)/i);
    const relatedDroplets = relatedSection
      ? relatedSection[1].match(/#(\d+)\s+([^(\n]+)/g)?.map(d => d.trim()) || []
      : [];

    const sprintMatch = content.match(/\*\*Current Sprint:\*\*\s*(.+)/i);

    const techStackSection = content.match(/## \d+\.\s*TECH STACK\s*([\s\S]*?)(?=\n##|\n---)/i);
    const techStack = techStackSection
      ? techStackSection[1].match(/\*\*([^:*]+):\*\*/g)?.map(t => t.replace(/\*\*/g, '').replace(':', '').trim()) || []
      : [];

    if (!idMatch) return null;

    return {
      id: parseInt(idMatch[1]),
      name: nameMatch?.[1]?.trim() || 'Unknown',
      repo,
      purpose: purposeMatch?.[1]?.trim() || '',
      steward: stewardMatch?.[1]?.trim() || '',
      status: statusMatch?.[1]?.trim() || 'UNKNOWN',
      liveEndpoint: endpointMatch?.[1]?.trim(),
      healthcheck: healthMatch?.[1]?.trim(),
      upstreamDependencies: upstreamDeps,
      relatedDroplets,
      currentSprint: sprintMatch?.[1]?.trim(),
      techStack,
      complianceScore: complianceMatch?.[1]?.trim(),
    };
  } catch (error) {
    console.error(`Error parsing README for ${repo}:`, error);
    return null;
  }
}
