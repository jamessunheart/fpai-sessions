import { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, Clock, Shield, Calendar, Hash } from 'lucide-react';
import { useApi } from '../../../shared/hooks/useApi';
import { api } from '../../../lib/api';
import { Card, LoadingSpinner } from '../../../shared/components';
import { Proof } from '../../../types';

interface ProofModalProps {
  isOpen: boolean;
  onClose: () => void;
  sprintId: string;
  sprintName: string;
}

export default function ProofModal({ isOpen, onClose, sprintId, sprintName }: ProofModalProps) {
  const { data: proofsData, loading } = useApi(() => api.getProofs(), [isOpen]);
  const [relatedProofs, setRelatedProofs] = useState<Proof[]>([]);

  useEffect(() => {
    if (proofsData?.records && sprintId) {
      const filtered = proofsData.records.filter((proof: Proof) => 
        proof.fields.Sprint_ID === sprintId
      );
      setRelatedProofs(filtered);
    }
  }, [proofsData, sprintId]);

  const getResultIcon = (result?: string) => {
    if (!result) return <Clock className="text-gray-500" size={20} />;
    const lowerResult = result.toLowerCase();
    if (lowerResult.includes('passed') || lowerResult.includes('success')) {
      return <CheckCircle className="text-green-500" size={20} />;
    }
    if (lowerResult.includes('failed') || lowerResult.includes('error')) {
      return <XCircle className="text-red-500" size={20} />;
    }
    return <Clock className="text-yellow-500" size={20} />;
  };

  const getResultColor = (result?: string) => {
    if (!result) return 'bg-gray-100 text-gray-800 dark:bg-gray-500/20 dark:text-gray-400';
    const lowerResult = result.toLowerCase();
    if (lowerResult.includes('passed') || lowerResult.includes('success')) {
      return 'bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-400';
    }
    if (lowerResult.includes('failed') || lowerResult.includes('error')) {
      return 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400';
    }
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-500/20 dark:text-yellow-400';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    // You could add a toast notification here
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-white dark:bg-slate-800 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-black dark:text-white">Proof Submissions</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">{sprintName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X size={18} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(80vh-120px)]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner size="md" />
              <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading...</span>
            </div>
          ) : relatedProofs.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-gray-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3">
                <Shield className="text-gray-400" size={20} />
              </div>
              <h3 className="font-medium text-black dark:text-white mb-1">
                No Proofs Found
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                No submissions yet for this sprint.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex justify-center gap-6 mb-4 p-3 bg-gray-50 dark:bg-slate-800 rounded-lg">
                <div className="text-center">
                  <div className="text-lg font-semibold text-black dark:text-white">{relatedProofs.length}</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Total</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-green-600">
                    {relatedProofs.filter(p => p.fields.Result?.toLowerCase().includes('passed')).length}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Passed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-red-600">
                    {relatedProofs.filter(p => p.fields.Result?.toLowerCase().includes('failed')).length}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Failed</div>
                </div>
              </div>

              {/* Proof List */}
              <div className="space-y-2">
                {relatedProofs.map((proof, index) => (
                  <div key={proof.id} className="border border-gray-200 dark:border-slate-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getResultIcon(proof.fields.Result)}
                        <div>
                          <div className="font-medium text-sm text-black dark:text-white">
                            {proof.fields.Proof_ID || 'Unknown'}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {formatDate(proof.createdTime)}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 text-xs rounded-full ${getResultColor(proof.fields.Result)}`}>
                          {proof.fields.Result || 'Unknown'}
                        </span>
                        {proof.fields.Token && (
                          <button
                            onClick={() => copyToken(proof.fields.Token || '')}
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                            title="Copy token"
                          >
                            Copy Token
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-slate-700 p-3 flex justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 rounded-lg transition-colors text-black dark:text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}