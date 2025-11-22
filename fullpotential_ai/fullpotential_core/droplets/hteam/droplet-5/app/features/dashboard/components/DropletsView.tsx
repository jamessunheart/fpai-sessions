'use client';

import { useEffect, useState } from 'react';
import { ExternalLink, RefreshCw, ChevronDown, ChevronUp, Network, CheckCircle, AlertCircle, Copy, Check } from 'lucide-react';
import StatsCard from '../../../components/StatsCard';

interface Droplet {
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
  complianceScore?: string;
  techStack: string[];
}

export default function DropletsView() {
  const [droplets, setDroplets] = useState<Droplet[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [readmeCache, setReadmeCache] = useState<Record<number, string>>({});
  const [loadingReadme, setLoadingReadme] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchDroplets();
  }, []);

  const fetchDroplets = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/droplets');
      const data = await res.json();
      if (data.success) {
        setDroplets(data.droplets);
      }
    } catch (error) {
      console.error('Failed to fetch droplets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFullReadme = async (dropletId: number) => {
    if (readmeCache[dropletId]) return;
    setLoadingReadme(true);
    try {
      const res = await fetch(`/api/droplets/${dropletId}`);
      const data = await res.json();
      if (data.success) {
        setReadmeCache(prev => ({ ...prev, [dropletId]: data.readme }));
      }
    } catch (error) {
      console.error('Failed to fetch README:', error);
      setReadmeCache(prev => ({ ...prev, [dropletId]: 'Failed to load README' }));
    } finally {
      setLoadingReadme(false);
    }
  };

  const handleRowClick = (droplet: Droplet) => {
    if (expandedRow === droplet.id) {
      setExpandedRow(null);
    } else {
      setExpandedRow(droplet.id);
      fetchFullReadme(droplet.id);
    }
  };

  const copyToClipboard = (dropletId: number) => {
    navigator.clipboard.writeText(readmeCache[dropletId] || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      OPERATIONAL: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      DEGRADED: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      DOWN: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const operationalCount = droplets.filter(d => d.status === 'OPERATIONAL').length;
  const withSprintsCount = droplets.filter(d => d.currentSprint).length;
  const compliantCount = droplets.filter(d => d.complianceScore).length;

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Droplets"
          value={droplets.length}
          icon={Network}
          loading={loading}
        />
        <StatsCard
          title="Operational"
          value={operationalCount}
          change={`${((operationalCount / droplets.length) * 100 || 0).toFixed(0)}% healthy`}
          changeType="positive"
          icon={CheckCircle}
          loading={loading}
        />
        <StatsCard
          title="Active Sprints"
          value={withSprintsCount}
          change={`${withSprintsCount} in progress`}
          changeType="positive"
          icon={AlertCircle}
          loading={loading}
        />
        <StatsCard
          title="UDC Compliant"
          value={compliantCount}
          change={`${((compliantCount / droplets.length) * 100 || 0).toFixed(0)}% compliant`}
          changeType="positive"
          icon={CheckCircle}
          loading={loading}
        />
      </div>

      {/* Table Card */}
      <div className="bg-white dark:bg-slate-800 backdrop-blur-xl rounded-2xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Droplet Network</h2>
          <button
            onClick={fetchDroplets}
            className="px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm flex items-center gap-2 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 dark:bg-slate-900">
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300 w-12"></th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">ID</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Name</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Steward</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Purpose</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Dependencies</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Sprint</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Compliance</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {droplets.map((droplet) => (
                <>
                  <tr
                    key={droplet.id}
                    onClick={() => handleRowClick(droplet)}
                    className="border-b border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      {expandedRow === droplet.id ? (
                        <ChevronUp className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono font-bold text-primary-600 dark:text-primary-400">#{droplet.id}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">{droplet.name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">{droplet.repo}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadge(droplet.status)}`}>
                        {droplet.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{droplet.steward}</td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="text-slate-600 dark:text-slate-400 line-clamp-2 text-xs">
                        {droplet.purpose || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        {droplet.upstreamDependencies.length > 0 ? (
                          <div className="space-y-1">
                            {droplet.upstreamDependencies.slice(0, 2).map((dep, i) => (
                              <div key={i}>{dep}</div>
                            ))}
                            {droplet.upstreamDependencies.length > 2 && (
                              <div className="text-primary-600 dark:text-primary-400">
                                +{droplet.upstreamDependencies.length - 2} more
                              </div>
                            )}
                          </div>
                        ) : (
                          '-'
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                        {droplet.currentSprint || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-green-600 dark:text-green-400">
                        {droplet.complianceScore || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {droplet.liveEndpoint && (
                        <a
                          href={droplet.liveEndpoint}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-primary-600 hover:text-primary-700 dark:text-primary-400"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}
                    </td>
                  </tr>
                  
                  {expandedRow === droplet.id && (
                    <tr className="bg-slate-50 dark:bg-slate-900">
                      <td colSpan={10} className="px-4 py-6">
                        <div className="grid grid-cols-2 gap-6">
                          <div className="space-y-4">
                            <h3 className="text-lg font-bold gradient-text">Droplet Information</h3>
                            
                            <div>
                              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Full Purpose</label>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{droplet.purpose || 'No purpose defined'}</p>
                            </div>

                            {droplet.upstreamDependencies.length > 0 && (
                              <div>
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">All Dependencies ({droplet.upstreamDependencies.length})</label>
                                <div className="mt-2 space-y-1">
                                  {droplet.upstreamDependencies.map((dep, i) => (
                                    <div key={i} className="px-3 py-2 bg-white dark:bg-slate-800 rounded-lg text-sm text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shadow-sm">
                                      {dep}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {droplet.relatedDroplets.length > 0 && (
                              <div>
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Related Droplets</label>
                                <div className="mt-2 space-y-1">
                                  {droplet.relatedDroplets.map((rel, i) => (
                                    <div key={i} className="px-3 py-2 bg-white dark:bg-slate-800 rounded-lg text-sm text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shadow-sm">
                                      {rel}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {droplet.techStack.length > 0 && (
                              <div>
                                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Tech Stack</label>
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {droplet.techStack.map((tech, i) => (
                                    <span key={i} className="px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded text-xs">
                                      {tech}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            <div className="flex gap-2 pt-4">
                              {droplet.liveEndpoint && (
                                <a
                                  href={droplet.liveEndpoint}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm transition-colors"
                                >
                                  Open Live →
                                </a>
                              )}
                              {droplet.healthcheck && (
                                <a
                                  href={droplet.healthcheck}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300 rounded-lg text-sm transition-colors shadow-sm"
                                >
                                  Health Check
                                </a>
                              )}
                            </div>
                          </div>

                          <div>
                            <div className="flex items-center justify-between mb-4">
                              <h3 className="text-lg font-bold gradient-text">Full README</h3>
                              <button
                                onClick={() => copyToClipboard(droplet.id)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-white rounded-lg text-sm transition-colors shadow-sm"
                              >
                                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                {copied ? 'Copied!' : 'Copy'}
                              </button>
                            </div>
                            {loadingReadme && !readmeCache[droplet.id] ? (
                              <div className="flex items-center justify-center py-8">
                                <RefreshCw className="w-6 h-6 animate-spin text-primary-600" />
                              </div>
                            ) : (
                              <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 max-h-96 overflow-auto shadow-sm">
                                <pre className="text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap font-mono">
                                  {readmeCache[droplet.id] || 'No README content available'}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
