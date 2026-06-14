const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_ORG = process.env.GITHUB_ORG || 'fullpotential-ai';

export async function fetchReadme(repo: string) {
  console.log(`Fetching ${repo} with token: ${GITHUB_TOKEN ? 'SET' : 'MISSING'}`);
  
  const response = await fetch(
    `https://api.github.com/repos/${GITHUB_ORG}/${repo}/readme`,
    {
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: 'application/vnd.github.v3+json',
      },
      cache: 'no-store', // Disable caching
    }
  );

  if (!response.ok) {
    console.error(`GitHub API error for ${repo}: ${response.status}`);
    throw new Error(`GitHub API error: ${response.status}`);
  }

  const data = await response.json();
  const content = Buffer.from(data.content, 'base64').toString('utf-8');
  
  return {
    content,
    name: data.name,
    path: data.path,
    sha: data.sha,
  };
}

export async function fetchAllDroplets() {
  const dropletRepos = Array.from({ length: 20 }, (_, i) => `droplet-${i + 1}`);
  
  const results = await Promise.allSettled(
    dropletRepos.map(async (repo) => {
      const readme = await fetchReadme(repo);
      return { repo, readme };
    })
  );

  return results
    .filter((r): r is PromiseFulfilledResult<{ repo: string; readme: any }> => r.status === 'fulfilled')
    .map(r => r.value);
}
