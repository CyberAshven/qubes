import React, { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Qube } from '../../types';
import { GlassCard, GlassButton } from '../glass';
import { useAuth } from '../../hooks/useAuth';
import { useRelationshipUpdates } from '../../hooks/useRelationshipUpdates';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { NetworkGraph } from '../NetworkGraph';
import { RelationshipRadarChart } from '../RelationshipRadarChart';
import { RelationshipTimelineChart } from '../RelationshipTimelineChart';
import { PendingRequests } from '../connections/PendingRequests';
import { ConnectionsList } from '../connections/ConnectionsList';
import { DiscoveryBrowser } from '../connections/DiscoveryBrowser';
import { Connection, PendingIntroduction } from '../connections/ConnectionManager';

interface Relationship {
  entity_id: string;
  entity_name?: string;
  entity_type?: string;
  status: 'unmet' | 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'best_friend';
  trust: number;
  has_met: boolean;
  is_best_friend: boolean;
  messages_sent: number;
  messages_received: number;
  collaborations_successful: number;
  collaborations_failed: number;
  first_contact?: number;
  last_interaction?: number;
  days_known: number;
  // Core Trust Metrics (5) - foundational earned qualities
  honesty: number;
  reliability: number;
  support: number;
  loyalty: number;
  respect: number;
  // Social Metrics - Positive (14)
  friendship: number;
  affection: number;
  engagement: number;
  depth: number;
  humor: number;
  understanding: number;
  compatibility: number;
  admiration: number;
  warmth: number;
  openness: number;
  patience: number;
  empowerment: number;
  responsiveness: number;
  expertise: number;
  // Social Metrics - Negative (10)
  antagonism: number;
  resentment: number;
  annoyance: number;
  distrust: number;
  rivalry: number;
  tension: number;
  condescension: number;
  manipulation: number;
  dismissiveness: number;
  betrayal: number;
  // Additional stats
  collaborations?: number;
  response_time_avg?: number;
  interaction_frequency_per_day?: number;
  communication_style?: string;
  shared_experiences?: Array<any>;
}

interface RelationshipsTabProps {
  qubes: Qube[];
}

// Stable empty array to avoid infinite loops with Zustand selectors
const EMPTY_ARRAY: string[] = [];

export const RelationshipsTab: React.FC<RelationshipsTabProps> = ({ qubes }) => {
  const { userId, password } = useAuth();
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab[state.currentTab] ?? EMPTY_ARRAY);
  const selectedQubeId = selectedQubeIds.length > 0 ? selectedQubeIds[0] : null;
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedRelationships, setExpandedRelationships] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'grid' | 'network' | 'connect'>('grid');

  // Connection state (for Connect mode)
  const [connections, setConnections] = useState<Connection[]>([]);
  const [pendingIntroductions, setPendingIntroductions] = useState<PendingIntroduction[]>([]);
  const [onlineQubes, setOnlineQubes] = useState<string[]>([]);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connectSubTab, setConnectSubTab] = useState<'connections' | 'pending' | 'discover'>('connections');
  const [timelineData, setTimelineData] = useState<Record<string, any[]>>({});

  const loadRelationships = useCallback(async (qubeId: string) => {
    try {
      setLoading(true);
      const params: any = {
        userId,
        qubeId,
      };

      // Only include password if it exists
      if (password) {
        params.password = password;
      }

      const result = await invoke<{
        success: boolean;
        relationships: Relationship[];
        stats: any;
        error?: string;
      }>('get_qube_relationships', params);

      if (result.success) {
        setRelationships(result.relationships);
        console.log('✅ Loaded relationships:', result.relationships.length);
      } else {
        console.error('❌ Failed to load relationships:', result.error);
        setRelationships([]);
      }
    } catch (error) {
      console.error('❌ Exception loading relationships:', error);
      setRelationships([]);
    } finally {
      setLoading(false);
    }
  }, [userId, password]);

  const loadTimelineData = useCallback(async (qubeId: string, entityId: string) => {
    try {
      const params: any = {
        userId,
        qubeId,
        entityId,
      };

      // Only include password if it exists
      if (password) {
        params.password = password;
      }

      const result = await invoke<{
        success: boolean;
        timeline: Array<{
          block_number: number;
          timestamp: number;
          trust: number;
          compatibility: number;
        }>;
        error?: string;
      }>('get_relationship_timeline', params);

      if (result.success && result.timeline.length > 0) {
        // Format timeline data for the chart
        const formattedData = result.timeline.map(point => ({
          date: new Date(point.timestamp * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          trust: point.trust,
          compatibility: point.compatibility,
        }));

        setTimelineData(prev => ({
          ...prev,
          [entityId]: formattedData
        }));

        console.log(`✅ Loaded ${formattedData.length} timeline points for ${entityId}`);
        return formattedData;
      } else {
        console.log(`No timeline data available for ${entityId}`);
        return null;
      }
    } catch (error) {
      console.error('❌ Exception loading timeline:', error);
      return null;
    }
  }, [userId, password]);

  // WebSocket connection for real-time updates (disabled by default)
  const { isConnected } = useRelationshipUpdates({
    onUpdate: (update) => {
      console.log('Received relationship update:', update);

      // Only reload if the update is for the currently selected qube
      if (update.data?.qube_id === selectedQubeId && selectedQubeId) {
        console.log('Reloading relationships for current qube');
        loadRelationships(selectedQubeId);
      }
    },
    autoConnect: false, // Disabled until WebSocket server is running
  });

  // Load relationships when qube is selected from roster
  useEffect(() => {
    if (selectedQubeId) {
      loadRelationships(selectedQubeId);
    }
  }, [selectedQubeId, loadRelationships]);

  // Load timeline data for all relationships
  useEffect(() => {
    if (selectedQubeId && relationships.length > 0) {
      // Load timeline for each relationship
      relationships.forEach(rel => {
        if (!timelineData[rel.entity_id]) {
          loadTimelineData(selectedQubeId, rel.entity_id);
        }
      });
    }
  }, [selectedQubeId, relationships, timelineData, loadTimelineData]);

  const selectedQube = qubes.find(q => q.qube_id === selectedQubeId);
  const isMinted = selectedQube?.nft_category_id && selectedQube.nft_category_id !== 'pending_minting';

  // Connection functions (for Connect mode)
  const fetchConnections = useCallback(async () => {
    if (!selectedQube || !userId) return;
    try {
      const result = await invoke<{ success: boolean; connections?: Connection[]; error?: string }>(
        'get_connections',
        { userId, qubeId: selectedQube.qube_id }
      );
      if (result.success && result.connections) {
        setConnections(result.connections);
      }
    } catch (err) {
      console.error('Failed to fetch connections:', err);
    }
  }, [selectedQube, userId]);

  const fetchPendingIntroductions = useCallback(async () => {
    if (!selectedQube || !userId || !password || !isMinted) return;
    try {
      const result = await invoke<{ success: boolean; pending?: PendingIntroduction[]; error?: string }>(
        'get_pending_introductions',
        { userId, qubeId: selectedQube.qube_id, password }
      );
      if (result.success && result.pending) {
        setPendingIntroductions(result.pending);
      }
    } catch (err) {
      console.error('Failed to fetch pending introductions:', err);
    }
  }, [selectedQube, userId, password, isMinted]);

  const fetchOnlineQubes = useCallback(async () => {
    if (!userId) return;
    try {
      const result = await invoke<{ success: boolean; online?: string[]; error?: string }>(
        'get_online_qubes',
        { userId }
      );
      if (result.success && result.online) {
        setOnlineQubes(result.online);
      }
    } catch (err) {
      console.error('Failed to fetch online qubes:', err);
    }
  }, [userId]);

  // Load connections when in connect mode
  useEffect(() => {
    if (viewMode === 'connect' && selectedQube) {
      fetchConnections();
      fetchPendingIntroductions();
      fetchOnlineQubes();

      // Poll for updates every 30 seconds
      const interval = setInterval(() => {
        fetchPendingIntroductions();
        fetchOnlineQubes();
      }, 30000);

      return () => clearInterval(interval);
    }
  }, [viewMode, selectedQube, fetchConnections, fetchPendingIntroductions, fetchOnlineQubes]);

  const handleAcceptIntroduction = async (relayId: string) => {
    if (!selectedQube || !userId || !password) return;
    setConnectLoading(true);
    setConnectError(null);
    try {
      const result = await invoke<{ success: boolean; from_name?: string; error?: string }>(
        'accept_introduction',
        { userId, qubeId: selectedQube.qube_id, relayId, password }
      );
      if (result.success) {
        await fetchConnections();
        await fetchPendingIntroductions();
      } else {
        setConnectError(result.error || 'Failed to accept introduction');
      }
    } catch (err) {
      setConnectError(String(err));
    } finally {
      setConnectLoading(false);
    }
  };

  const handleRejectIntroduction = async (relayId: string) => {
    if (!selectedQube || !userId || !password) return;
    setConnectLoading(true);
    setConnectError(null);
    try {
      const result = await invoke<{ success: boolean; error?: string }>(
        'reject_introduction',
        { userId, qubeId: selectedQube.qube_id, relayId, password }
      );
      if (result.success) {
        await fetchPendingIntroductions();
      } else {
        setConnectError(result.error || 'Failed to reject introduction');
      }
    } catch (err) {
      setConnectError(String(err));
    } finally {
      setConnectLoading(false);
    }
  };

  const handleSendIntroduction = async (toCommitment: string, message: string) => {
    if (!selectedQube || !userId || !password) return;
    setConnectLoading(true);
    setConnectError(null);
    try {
      const result = await invoke<{ success: boolean; relay_id?: string; error?: string }>(
        'send_introduction',
        { userId, qubeId: selectedQube.qube_id, toCommitment, message, password }
      );
      if (result.success) {
        setConnectSubTab('pending');
      } else {
        setConnectError(result.error || 'Failed to send introduction');
      }
    } catch (err) {
      setConnectError(String(err));
    } finally {
      setConnectLoading(false);
    }
  };

  const toggleRelationship = (entityId: string) => {
    setExpandedRelationships(prev => {
      const newSet = new Set(prev);
      if (newSet.has(entityId)) {
        newSet.delete(entityId);
      } else {
        newSet.add(entityId);
      }
      return newSet;
    });
  };

  // Filter out self-relationships and deduplicate by Qube identity
  // In P2P mode, the same Qube might have relationships recorded with both qube_id and commitment
  const filteredRelationships = (() => {
    if (!selectedQube) return relationships;

    // First filter out self-relationships
    const nonSelfRelationships = relationships.filter(rel =>
      rel.entity_id !== selectedQube.qube_id &&
      rel.entity_id !== selectedQube.commitment
    );

    // Deduplicate: if two relationships point to the same Qube (one by qube_id, one by commitment),
    // merge them by keeping the one with higher trust/more interactions
    const seenQubeIds = new Map<string, Relationship>(); // canonical qube_id -> best relationship

    for (const rel of nonSelfRelationships) {
      // Try to find the canonical Qube this relationship points to
      const qube = qubes.find(q => q.qube_id === rel.entity_id || q.commitment === rel.entity_id);
      const canonicalId = qube?.qube_id || rel.entity_id;

      const existing = seenQubeIds.get(canonicalId);
      if (!existing) {
        seenQubeIds.set(canonicalId, rel);
      } else {
        // Keep the relationship with more data (higher trust, more messages)
        const existingScore = existing.trust + existing.messages_sent + existing.messages_received;
        const newScore = rel.trust + rel.messages_sent + rel.messages_received;
        if (newScore > existingScore) {
          seenQubeIds.set(canonicalId, rel);
        }
      }
    }

    return Array.from(seenQubeIds.values());
  })();

  // Group relationships by status
  const groupedRelationships = filteredRelationships.reduce((groups, rel) => {
    const status = rel.status;
    if (!groups[status]) {
      groups[status] = [];
    }
    groups[status].push(rel);
    return groups;
  }, {} as Record<string, Relationship[]>);

  // Status order and display config
  const statusConfig = [
    { status: 'best_friend', label: 'Best Friend', icon: '💖', color: '#ff69b4' },
    { status: 'close_friend', label: 'Close Friends', icon: '💕', color: '#ff1493' },
    { status: 'friend', label: 'Friends', icon: '💚', color: '#00ff88' },
    { status: 'acquaintance', label: 'Acquaintances', icon: '👋', color: '#ffaa00' },
    { status: 'stranger', label: 'Strangers', icon: '🤝', color: '#888888' },
    { status: 'unmet', label: 'Unmet', icon: '❓', color: '#666666' },
  ];

  const getTrustColor = (trust: number): string => {
    if (trust >= 75) return '#00ff88';
    if (trust >= 50) return '#ffaa00';
    if (trust >= 25) return '#ff8800';
    return '#ff3366';
  };

  const formatDate = (timestamp?: number): string => {
    if (!timestamp) return 'Never';
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const getRelationshipDuration = (firstContact?: number): string => {
    if (!firstContact) return 'N/A';
    const days = Math.floor((Date.now() / 1000 - firstContact) / 86400);
    if (days === 0) return 'Today';
    if (days === 1) return '1 day';
    if (days < 30) return `${days} days`;
    const months = Math.floor(days / 30);
    if (months === 1) return '1 month';
    if (months < 12) return `${months} months`;
    const years = Math.floor(months / 12);
    return years === 1 ? '1 year' : `${years} years`;
  };

  const formatResponseTime = (seconds?: number): string => {
    if (!seconds || seconds === 0) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
  };

  const ProgressBar = ({ value, max = 100, color }: { value: number; max?: number; color?: string }) => {
    const percentage = (value / max) * 100;
    const barColor = color || getTrustColor(value);

    return (
      <div className="w-full bg-glass-bg rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: barColor
          }}
        />
      </div>
    );
  };

  const getEntityNameColor = (rel: Relationship): string => {
    // Human names stay white
    if (rel.entity_type === 'human') {
      return 'text-text-primary';
    }

    // Qube names use their favorite color
    // Check by qube_id first, then by commitment (for P2P relationships)
    const qube = qubes.find(q => q.qube_id === rel.entity_id || q.commitment === rel.entity_id);
    if (qube?.favorite_color) {
      return ''; // Return empty to use inline style
    }

    return 'text-text-primary';
  };

  const getEntityNameStyle = (rel: Relationship): React.CSSProperties => {
    if (rel.entity_type === 'qube') {
      const qube = qubes.find(q => q.qube_id === rel.entity_id || q.commitment === rel.entity_id);
      if (qube?.favorite_color) {
        return { color: qube.favorite_color };
      }
    }
    return {};
  };

  // Get display name for a relationship - shows "Name (ID)" for Qubes
  const getEntityDisplayName = (rel: Relationship): string => {
    // For human entities, just show the name/id
    if (rel.entity_type === 'human') {
      return rel.entity_name || rel.entity_id;
    }

    // For Qube entities, try to find full info
    // Check by qube_id first, then by commitment (for P2P relationships)
    const qube = qubes.find(q => q.qube_id === rel.entity_id || q.commitment === rel.entity_id);

    if (qube) {
      // Found the qube - show "Name (short_id)"
      const shortId = qube.qube_id.substring(0, 8);
      return `${qube.name} (${shortId})`;
    }

    // If entity_name is available, use it with the ID
    if (rel.entity_name) {
      // Truncate entity_id if it's too long (commitments are 64 chars)
      const shortId = rel.entity_id.length > 8 ? rel.entity_id.substring(0, 8) + '...' : rel.entity_id;
      return `${rel.entity_name} (${shortId})`;
    }

    // Fallback: just show truncated ID
    return rel.entity_id.length > 12 ? rel.entity_id.substring(0, 12) + '...' : rel.entity_id;
  };

  // Get timeline data - only show real data from snapshots
  const generateTimelineData = (rel: Relationship) => {
    // Check if we have real timeline data loaded
    if (timelineData[rel.entity_id] && timelineData[rel.entity_id].length > 0) {
      console.log(`Using real timeline data for ${rel.entity_name}: ${timelineData[rel.entity_id].length} points`);
      return timelineData[rel.entity_id];
    }

    // Load real data in the background
    if (selectedQubeId) {
      loadTimelineData(selectedQubeId, rel.entity_id);
    }

    // Return empty array if no real data available
    // Timeline chart will show "No timeline data available" message
    console.log(`No timeline data yet for ${rel.entity_name} - will show once snapshots are created`);
    return [];
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-6 pb-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-display text-text-primary mb-1">
              Relationships
            </h1>
            <p className="text-sm text-text-secondary">
              {selectedQube ? `${selectedQube.name}'s relationships` : 'Select a qube to view relationships'}
            </p>
          </div>

          {/* WebSocket Connection Status */}
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-gray-500'} ${isConnected ? 'animate-pulse' : ''}`} />
            <span className="text-text-tertiary">
              {isConnected ? 'Live updates' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Relationship count and view toggle */}
        {selectedQube && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-text-tertiary">
              <span className="text-accent-primary font-medium">
                {filteredRelationships.length}
              </span>
              <span>relationships</span>
            </div>

            {/* View Mode Toggle */}
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded text-xs transition-colors ${
                  viewMode === 'grid'
                    ? 'bg-accent-primary text-white'
                    : 'bg-glass-bg text-text-tertiary hover:text-text-primary'
                }`}
              >
                📋 Grid
              </button>
              <button
                onClick={() => setViewMode('network')}
                className={`px-3 py-1.5 rounded text-xs transition-colors ${
                  viewMode === 'network'
                    ? 'bg-accent-primary text-white'
                    : 'bg-glass-bg text-text-tertiary hover:text-text-primary'
                }`}
              >
                🌐 Network
              </button>
              <button
                onClick={() => setViewMode('connect')}
                className={`px-3 py-1.5 rounded text-xs transition-colors ${
                  viewMode === 'connect'
                    ? 'bg-accent-primary text-white'
                    : 'bg-glass-bg text-text-tertiary hover:text-text-primary'
                }`}
              >
                🔗 Connect
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden px-6 pb-6">
        {!selectedQubeId ? (
          <GlassCard className="p-12 text-center">
            <div className="text-6xl mb-4">👈</div>
            <h2 className="text-2xl font-display text-text-primary mb-2">
              Select a Qube
            </h2>
            <p className="text-text-secondary">
              Choose a qube from the roster to view its relationships
            </p>
          </GlassCard>
        ) : viewMode === 'connect' ? (
          /* Connect Mode Content */
          !isMinted ? (
            <GlassCard className="p-6 text-center">
              <h2 className="text-xl font-display text-accent-warning mb-4">
                NFT Required
              </h2>
              <p className="text-text-secondary mb-4">
                {selectedQube?.name} must be minted as an NFT before connecting with other Qubes.
              </p>
              <p className="text-sm text-text-tertiary">
                Go to the Dashboard tab and click "Mint NFT" to get started.
              </p>
            </GlassCard>
          ) : (
            <div className="h-full flex flex-col">
              {/* Connect Error Display */}
              {connectError && (
                <div className="mb-4 p-3 bg-accent-danger/20 border border-accent-danger/50 rounded-lg">
                  <p className="text-accent-danger text-sm">{connectError}</p>
                </div>
              )}

              {/* Connect Sub-tabs */}
              <div className="flex gap-2 mb-4">
                <GlassButton
                  variant={connectSubTab === 'connections' ? 'primary' : 'secondary'}
                  onClick={() => setConnectSubTab('connections')}
                  className="flex-1"
                >
                  Connections ({connections.length})
                </GlassButton>
                <GlassButton
                  variant={connectSubTab === 'pending' ? 'primary' : 'secondary'}
                  onClick={() => setConnectSubTab('pending')}
                  className="flex-1"
                >
                  Pending ({pendingIntroductions.length})
                </GlassButton>
                <GlassButton
                  variant={connectSubTab === 'discover' ? 'primary' : 'secondary'}
                  onClick={() => setConnectSubTab('discover')}
                  className="flex-1"
                >
                  Discover
                </GlassButton>
              </div>

              {/* Connect Sub-tab Content */}
              <div className="flex-1 overflow-y-auto">
                {connectSubTab === 'connections' && (
                  <ConnectionsList
                    connections={connections}
                    onlineQubes={onlineQubes}
                  />
                )}

                {connectSubTab === 'pending' && (
                  <PendingRequests
                    pending={pendingIntroductions}
                    onAccept={handleAcceptIntroduction}
                    onReject={handleRejectIntroduction}
                    loading={connectLoading}
                    qubeId={selectedQube!.qube_id}
                  />
                )}

                {connectSubTab === 'discover' && (
                  <DiscoveryBrowser
                    onSendIntroduction={handleSendIntroduction}
                    onlineQubes={onlineQubes}
                    existingConnections={connections.map(c => c.commitment)}
                    ownCommitment={selectedQube?.commitment || ''}
                    loading={connectLoading}
                    qubeId={selectedQube!.qube_id}
                  />
                )}
              </div>
            </div>
          )
        ) : loading ? (
          <GlassCard className="p-12 text-center">
            <p className="text-text-secondary">Loading relationships...</p>
          </GlassCard>
        ) : filteredRelationships.length === 0 ? (
          <GlassCard className="p-8 text-center">
            <div className="text-4xl mb-3">💬</div>
            <h3 className="text-lg font-display text-text-primary mb-1">
              No Relationships Yet
            </h3>
            <p className="text-sm text-text-secondary">
              Start conversations to build relationships
            </p>
          </GlassCard>
        ) : viewMode === 'network' ? (
          <div className="w-full" style={{ height: 'calc(100vh - 250px)' }}>
            <NetworkGraph
              relationships={filteredRelationships}
              centerQube={selectedQube!}
              allQubes={qubes}
              onNodeClick={(entityId) => {
                // Optionally expand that relationship in grid view or show details
                setExpandedRelationships(new Set([entityId]));
                setViewMode('grid');
              }}
            />
          </div>
        ) : (
          <div className="space-y-4 overflow-y-auto">
            {statusConfig.map(({ status, label, icon, color }) => {
              const group = groupedRelationships[status] || [];
              if (group.length === 0) return null;

              return (
                <div key={status}>
                  <div className="flex items-center gap-2 mb-2 px-2">
                    <span className="text-xl">{icon}</span>
                    <h3 className="text-sm font-semibold text-text-primary">
                      {label}
                    </h3>
                    <span className="text-xs text-text-tertiary">
                      ({group.length})
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-start">
                    {group.map((rel, index) => {
                      // Use a unique key combining entity_id and index to ensure uniqueness
                      const uniqueKey = `${rel.entity_id}-${index}`;
                      const isExpanded = expandedRelationships.has(uniqueKey);
                      const statusIcon = statusConfig.find(s => s.status === rel.status)?.icon || '🤝';

                      return (
                        <GlassCard key={uniqueKey} className="overflow-hidden">
                          {/* Collapsible Header */}
                          <div
                            className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/5 transition-colors"
                            onClick={() => toggleRelationship(uniqueKey)}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-xl flex-shrink-0">{statusIcon}</span>
                              <h3
                                className={`text-base font-display truncate ${getEntityNameColor(rel)}`}
                                style={getEntityNameStyle(rel)}
                              >
                                {getEntityDisplayName(rel)}
                              </h3>
                            </div>
                            <span className="text-lg text-text-tertiary flex-shrink-0">
                              {isExpanded ? '▼' : '▶'}
                            </span>
                          </div>

                          {/* Expandable Content */}
                          {isExpanded && (
                            <div className="px-3 pb-3 space-y-3 text-xs max-h-[600px] overflow-y-auto">
                              {/* Key Metrics Overview - Overall Trust & Compatibility */}
                              <div className="pb-3 border-b border-glass-border/50">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-text-tertiary font-semibold">Overall Trust:</span>
                                  <span className="text-text-primary font-semibold">
                                    {Math.round(rel.trust)}/100
                                  </span>
                                </div>
                                <ProgressBar value={rel.trust} color="#4CAF50" />

                                <div className="flex items-center justify-between mt-3 mb-1">
                                  <span className="text-text-tertiary font-semibold">Compatibility:</span>
                                  <span className="text-text-primary font-semibold">
                                    {Math.round(rel.compatibility)}/100
                                  </span>
                                </div>
                                <ProgressBar value={rel.compatibility} color="#00aaff" />

                                {rel.is_best_friend && (
                                  <div className="mt-3 text-center">
                                    <span className="text-xs bg-pink-500/20 text-pink-300 px-2 py-1 rounded">
                                      ⭐ Best Friend
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* Radar Chart Visualization - Core Trust Components */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2 text-center">
                                  Core Trust Profile
                                </h4>
                                <RelationshipRadarChart
                                  reliability={rel.reliability}
                                  honesty={rel.honesty}
                                  loyalty={rel.loyalty}
                                  respect={rel.respect}
                                  expertise={rel.expertise}
                                  color={getEntityNameStyle(rel).color || '#4A90E2'}
                                />
                              </div>

                              {/* Core Trust (5 metrics) - Foundational Earned Qualities */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">
                                  🔒 Core Trust
                                </h4>
                                <div className="space-y-2">
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Honesty:</span>
                                      <span className="text-text-primary">{Math.round(rel.honesty)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.honesty} color="#2196F3" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Reliability:</span>
                                      <span className="text-text-primary">{Math.round(rel.reliability)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.reliability} color="#4CAF50" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Support:</span>
                                      <span className="text-text-primary">{Math.round(rel.support)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.support} color="#ff6347" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Loyalty:</span>
                                      <span className="text-text-primary">{Math.round(rel.loyalty)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.loyalty} color="#dc143c" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Respect:</span>
                                      <span className="text-text-primary">{Math.round(rel.respect)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.respect} color="#ba55d3" />
                                  </div>
                                </div>
                              </div>

                              {/* Emotional Bond (4 metrics) */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">
                                  💖 Emotional Bond
                                </h4>
                                <div className="space-y-2">
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Friendship:</span>
                                      <span className="text-text-primary">{Math.round(rel.friendship)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.friendship} color="#ff69b4" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Affection:</span>
                                      <span className="text-text-primary">{Math.round(rel.affection)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.affection} color="#ff1493" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Warmth:</span>
                                      <span className="text-text-primary">{Math.round(rel.warmth)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.warmth} color="#ffa07a" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Understanding:</span>
                                      <span className="text-text-primary">{Math.round(rel.understanding)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.understanding} color="#ff8c69" />
                                  </div>
                                </div>
                              </div>

                              {/* Personal Growth (4 metrics) */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">
                                  🌱 Personal Growth
                                </h4>
                                <div className="space-y-2">
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Admiration:</span>
                                      <span className="text-text-primary">{Math.round(rel.admiration)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.admiration} color="#ffd700" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Empowerment:</span>
                                      <span className="text-text-primary">{Math.round(rel.empowerment)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.empowerment} color="#32cd32" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Openness:</span>
                                      <span className="text-text-primary">{Math.round(rel.openness)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.openness} color="#87ceeb" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Patience:</span>
                                      <span className="text-text-primary">{Math.round(rel.patience)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.patience} color="#9370db" />
                                  </div>
                                </div>
                              </div>

                              {/* Connection Quality (6 metrics) */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">
                                  ✨ Connection Quality
                                </h4>
                                <div className="space-y-2">
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Engagement:</span>
                                      <span className="text-text-primary">{Math.round(rel.engagement)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.engagement} color="#00bcd4" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Depth:</span>
                                      <span className="text-text-primary">{Math.round(rel.depth)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.depth} color="#3f51b5" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Humor:</span>
                                      <span className="text-text-primary">{Math.round(rel.humor)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.humor} color="#ffeb3b" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Compatibility:</span>
                                      <span className="text-text-primary">{Math.round(rel.compatibility)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.compatibility} color="#20b2aa" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Responsiveness:</span>
                                      <span className="text-text-primary">{Math.round(rel.responsiveness)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.responsiveness} color="#00ff7f" />
                                  </div>
                                  <div>
                                    <div className="flex justify-between mb-1">
                                      <span className="text-text-tertiary">Expertise:</span>
                                      <span className="text-text-primary">{Math.round(rel.expertise)}/100</span>
                                    </div>
                                    <ProgressBar value={rel.expertise} color="#9C27B0" />
                                  </div>
                                </div>

                                {/* Timeline Chart */}
                                {timelineData[rel.entity_id] && timelineData[rel.entity_id].length > 0 && (
                                  <div className="pt-3 border-t border-glass-border/50 mt-3">
                                    <h4 className="text-text-secondary font-semibold mb-2 text-center">
                                      Relationship Progression
                                    </h4>
                                    <RelationshipTimelineChart
                                      data={timelineData[rel.entity_id]}
                                      color={getEntityNameStyle(rel).color || '#4A90E2'}
                                    />
                                  </div>
                                )}
                              </div>

                              {/* Negative Dynamics (10 metrics) */}
                              {(rel.antagonism > 0 || rel.resentment > 0 || rel.annoyance > 0 ||
                                rel.distrust > 0 || rel.rivalry > 0 || rel.tension > 0 ||
                                rel.condescension > 0 || rel.manipulation > 0 ||
                                rel.dismissiveness > 0 || rel.betrayal > 0) && (
                                <div className="pt-3 border-t border-glass-border/50">
                                  <h4 className="text-text-secondary font-semibold mb-2">
                                    ⚠️ Negative Dynamics
                                  </h4>
                                  <div className="space-y-2">
                                    {rel.antagonism > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Antagonism:</span>
                                          <span className="text-red-400">{Math.round(rel.antagonism)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.antagonism} color="#dc143c" />
                                      </div>
                                    )}
                                    {rel.resentment > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Resentment:</span>
                                          <span className="text-red-400">{Math.round(rel.resentment)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.resentment} color="#b22222" />
                                      </div>
                                    )}
                                    {rel.annoyance > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Annoyance:</span>
                                          <span className="text-orange-400">{Math.round(rel.annoyance)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.annoyance} color="#ff6347" />
                                      </div>
                                    )}
                                    {rel.distrust > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Distrust:</span>
                                          <span className="text-red-400">{Math.round(rel.distrust)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.distrust} color="#8b0000" />
                                      </div>
                                    )}
                                    {rel.rivalry > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Rivalry:</span>
                                          <span className="text-yellow-400">{Math.round(rel.rivalry)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.rivalry} color="#daa520" />
                                      </div>
                                    )}
                                    {rel.tension > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Tension:</span>
                                          <span className="text-orange-400">{Math.round(rel.tension)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.tension} color="#ff4500" />
                                      </div>
                                    )}
                                    {rel.condescension > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Condescension:</span>
                                          <span className="text-red-400">{Math.round(rel.condescension)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.condescension} color="#cd5c5c" />
                                      </div>
                                    )}
                                    {rel.manipulation > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Manipulation:</span>
                                          <span className="text-red-400">{Math.round(rel.manipulation)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.manipulation} color="#8b0000" />
                                      </div>
                                    )}
                                    {rel.dismissiveness > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Dismissiveness:</span>
                                          <span className="text-orange-400">{Math.round(rel.dismissiveness)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.dismissiveness} color="#ff6347" />
                                      </div>
                                    )}
                                    {rel.betrayal > 0 && (
                                      <div>
                                        <div className="flex justify-between mb-1">
                                          <span className="text-text-tertiary">Betrayal:</span>
                                          <span className="text-red-500 font-bold">{Math.round(rel.betrayal)}/100</span>
                                        </div>
                                        <ProgressBar value={rel.betrayal} color="#800000" />
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Communication Stats */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">Communication:</h4>
                                <div className="space-y-1.5">
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Messages Sent:</span>
                                    <span className="text-text-primary">{rel.messages_sent}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Messages Received:</span>
                                    <span className="text-text-primary">{rel.messages_received}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Collaboration Stats */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">Collaboration:</h4>
                                <div className="space-y-1.5">
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Successful Tasks:</span>
                                    <span className="text-green-400">{rel.collaborations_successful}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Failed Tasks:</span>
                                    <span className="text-red-400">{rel.collaborations_failed}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Relationship Insights */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">Relationship Insights:</h4>
                                <div className="space-y-1.5">
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Duration:</span>
                                    <span className="text-text-primary">{getRelationshipDuration(rel.first_contact)}</span>
                                  </div>
                                  {(rel.shared_experiences && rel.shared_experiences.length > 0) && (
                                    <div className="flex justify-between">
                                      <span className="text-text-tertiary">Shared Experiences:</span>
                                      <span className="text-accent-primary">{rel.shared_experiences.length}</span>
                                    </div>
                                  )}
                                  {(rel.interaction_frequency_per_day !== undefined && rel.interaction_frequency_per_day > 0) && (
                                    <div className="flex justify-between">
                                      <span className="text-text-tertiary">Daily Interactions:</span>
                                      <span className="text-text-primary">{rel.interaction_frequency_per_day.toFixed(1)}</span>
                                    </div>
                                  )}
                                  {(rel.response_time_avg !== undefined && rel.response_time_avg > 0) && (
                                    <div className="flex justify-between">
                                      <span className="text-text-tertiary">Avg Response Time:</span>
                                      <span className="text-text-primary">{formatResponseTime(rel.response_time_avg)}</span>
                                    </div>
                                  )}
                                  {rel.communication_style && rel.communication_style !== 'unknown' && (
                                    <div className="flex justify-between">
                                      <span className="text-text-tertiary">Style:</span>
                                      <span className="text-text-primary capitalize">{rel.communication_style}</span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Timeline */}
                              <div className="pt-3 border-t border-glass-border/50">
                                <h4 className="text-text-secondary font-semibold mb-2">Timeline:</h4>
                                <div className="space-y-1.5">
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">First Contact:</span>
                                    <span className="text-text-primary">{formatDate(rel.first_contact)}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-text-tertiary">Last Interaction:</span>
                                    <span className="text-text-primary">{formatDate(rel.last_interaction)}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </GlassCard>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
