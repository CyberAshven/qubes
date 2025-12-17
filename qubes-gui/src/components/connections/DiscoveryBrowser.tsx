import { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { GlassCard, GlassButton, GlassInput } from '../glass';
import { useAuth } from '../../hooks/useAuth';

interface BCMRQube {
  commitment: string;
  name: string;
  description: string;
  avatar?: string;
  qube_id?: string;
  creator?: string;
}

interface DiscoveryBrowserProps {
  onSendIntroduction: (toCommitment: string, message: string) => void;
  onlineQubes: string[];
  existingConnections: string[];
  ownCommitment: string;
  loading: boolean;
  qubeId: string;
}

const BCMR_URL = 'https://qube.cash/.well-known/bitcoin-cash-metadata-registry.json';
const CATEGORY_ID = 'c9054d53dcc075dd7226ea319f20d43df102371149311c9239f6c0ea1200b80f';

export const DiscoveryBrowser: React.FC<DiscoveryBrowserProps> = ({
  onSendIntroduction,
  onlineQubes,
  existingConnections,
  ownCommitment,
  loading,
  qubeId,
}) => {
  const { userId, password } = useAuth();
  const [qubes, setQubes] = useState<BCMRQube[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterOnline, setFilterOnline] = useState(false);
  const [fetchingRegistry, setFetchingRegistry] = useState(true);
  const [selectedQube, setSelectedQube] = useState<BCMRQube | null>(null);
  const [introMessage, setIntroMessage] = useState('');
  const [generatingIntro, setGeneratingIntro] = useState(false);
  const [introGenerated, setIntroGenerated] = useState(false);

  // Fetch BCMR registry
  useEffect(() => {
    const fetchRegistry = async () => {
      try {
        const response = await fetch(BCMR_URL);
        const data = await response.json();

        // Parse BCMR structure
        const identity = data.identities?.[CATEGORY_ID];
        if (!identity) {
          console.error('Category not found in BCMR');
          return;
        }

        // Get the latest revision
        const revisionKeys = Object.keys(identity).filter(k => k !== '$schema');
        if (revisionKeys.length === 0) return;

        const latestRevision = revisionKeys.sort().pop();
        const tokenData = identity[latestRevision!];
        const types = tokenData?.nfts?.parse?.types || {};

        // Convert to array
        const qubeList: BCMRQube[] = Object.entries(types).map(([commitment, data]: [string, any]) => {
          // Extract qube_id and creator from attributes
          let qube_id = '';
          let creator = '';
          const attributes = data.extensions?.attributes || [];
          for (const attr of attributes) {
            if (attr.trait_type === 'Qube ID') qube_id = attr.value;
            if (attr.trait_type === 'Creator') creator = attr.value;
          }

          // Get avatar URL
          let avatar = undefined;
          if (data.uris?.icon) {
            const cid = data.uris.icon.replace('ipfs://', '');
            avatar = `https://ipfs.io/ipfs/${cid}`;
          }

          return {
            commitment,
            name: data.name || 'Unknown',
            description: data.description || '',
            avatar,
            qube_id,
            creator,
          };
        });

        setQubes(qubeList);
      } catch (err) {
        console.error('Failed to fetch BCMR:', err);
      } finally {
        setFetchingRegistry(false);
      }
    };

    fetchRegistry();
  }, []);

  // Filter qubes
  const filteredQubes = qubes.filter((qube) => {
    // Don't show own qube
    if (qube.commitment === ownCommitment) return false;

    // Don't show already connected qubes
    if (existingConnections.includes(qube.commitment)) return false;

    // Filter by online status
    if (filterOnline && !onlineQubes.includes(qube.commitment)) return false;

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        qube.name.toLowerCase().includes(query) ||
        qube.description.toLowerCase().includes(query) ||
        qube.commitment.toLowerCase().includes(query)
      );
    }

    return true;
  });

  // Generate AI introduction when a qube is selected
  const handleSelectQube = async (qube: BCMRQube) => {
    setSelectedQube(qube);
    setIntroMessage('');
    setIntroGenerated(false);
    setGeneratingIntro(true);

    try {
      const result = await invoke<{ success: boolean; message?: string; error?: string }>(
        'generate_introduction',
        {
          userId,
          qubeId,
          toCommitment: qube.commitment,
          toName: qube.name,
          toDescription: qube.description || '',
          password,
        }
      );

      if (result.success && result.message) {
        setIntroMessage(result.message);
        setIntroGenerated(true);
      } else {
        // Fallback to generic message if AI generation fails
        setIntroMessage(`Hello ${qube.name}! I'd like to connect with you.`);
        setIntroGenerated(false);
      }
    } catch (err) {
      console.error('Failed to generate introduction:', err);
      // Fallback to generic message
      setIntroMessage(`Hello ${qube.name}! I'd like to connect with you.`);
      setIntroGenerated(false);
    } finally {
      setGeneratingIntro(false);
    }
  };

  const handleSendIntroduction = () => {
    if (!selectedQube) return;
    onSendIntroduction(selectedQube.commitment, introMessage);
    setSelectedQube(null);
    setIntroMessage('');
    setIntroGenerated(false);
  };

  if (fetchingRegistry) {
    return (
      <GlassCard className="p-6 text-center">
        <p className="text-text-secondary">Loading registry...</p>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and filters */}
      <div className="flex gap-3">
        <GlassInput
          placeholder="Search Qubes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1"
        />
        <GlassButton
          variant={filterOnline ? 'primary' : 'secondary'}
          onClick={() => setFilterOnline(!filterOnline)}
        >
          Online Only ({onlineQubes.length})
        </GlassButton>
      </div>

      {/* Results count */}
      <p className="text-sm text-text-tertiary">
        {filteredQubes.length} Qube{filteredQubes.length !== 1 ? 's' : ''} found
      </p>

      {/* Qube list */}
      {filteredQubes.length === 0 ? (
        <GlassCard className="p-6 text-center">
          <p className="text-text-secondary">No Qubes found matching your criteria</p>
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {filteredQubes.map((qube) => {
            const isOnline = onlineQubes.includes(qube.commitment);

            return (
              <GlassCard key={qube.commitment} className="p-4">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-glass-medium overflow-hidden flex-shrink-0">
                    {qube.avatar ? (
                      <img
                        src={qube.avatar}
                        alt={qube.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-text-tertiary">
                        ?
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-display text-lg text-text-primary truncate">
                        {qube.name}
                      </h3>
                      {isOnline && (
                        <span className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
                      )}
                    </div>
                    <p className="text-sm text-text-secondary line-clamp-2">
                      {qube.description}
                    </p>
                    {qube.creator && (
                      <p className="text-xs text-text-tertiary mt-1">
                        Created by {qube.creator}
                      </p>
                    )}
                  </div>

                  {/* Action */}
                  <GlassButton
                    size="sm"
                    onClick={() => handleSelectQube(qube)}
                    disabled={loading || generatingIntro}
                  >
                    Connect
                  </GlassButton>
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}

      {/* Introduction Modal */}
      {selectedQube && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <GlassCard className="p-6 max-w-md mx-4">
            <h2 className="text-xl font-display text-text-primary mb-4">
              Send Introduction to {selectedQube.name}
            </h2>

            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm text-text-secondary">
                  Introduction Message
                </label>
                {introGenerated && (
                  <span className="text-xs text-accent-primary">
                    AI Generated
                  </span>
                )}
              </div>

              {generatingIntro ? (
                <div className="w-full p-6 bg-bg-tertiary border border-glass-border rounded-lg text-center">
                  <div className="animate-pulse text-text-secondary">
                    Your Qube is crafting a personalized introduction...
                  </div>
                </div>
              ) : (
                <textarea
                  value={introMessage}
                  onChange={(e) => {
                    setIntroMessage(e.target.value);
                    setIntroGenerated(false); // Mark as edited if user changes it
                  }}
                  className="w-full p-3 bg-bg-tertiary border border-glass-border rounded-lg text-white resize-none focus:outline-none focus:border-accent-primary"
                  rows={4}
                  placeholder="Your Qube's introduction message..."
                />
              )}

              {!generatingIntro && introGenerated && (
                <p className="text-xs text-text-tertiary mt-2">
                  You can edit this message before sending if you'd like.
                </p>
              )}
            </div>

            <div className="flex gap-3 justify-end">
              <GlassButton
                variant="secondary"
                onClick={() => {
                  setSelectedQube(null);
                  setIntroMessage('');
                  setIntroGenerated(false);
                }}
              >
                Cancel
              </GlassButton>
              <GlassButton
                variant="primary"
                onClick={handleSendIntroduction}
                disabled={loading || generatingIntro || !introMessage.trim()}
              >
                Send Introduction
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};
