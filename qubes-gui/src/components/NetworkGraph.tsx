import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Panel,
  Viewport,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './NetworkGraph.css';
import { Qube } from '../types';
import { NetworkBackground } from './NetworkBackground';

interface Relationship {
  entity_id: string;
  entity_name?: string;
  entity_type?: string;
  status: 'blocked' | 'enemy' | 'rival' | 'suspicious' | 'unmet' | 'stranger' | 'acquaintance' | 'friend' | 'close_friend' | 'best_friend';
  trust: number;
  friendship: number;
  messages_sent: number;
  messages_received: number;
  interaction_frequency_per_day?: number;
  // Clearance System (v2)
  clearance_profile?: 'none' | 'public' | 'professional' | 'social' | 'trusted' | 'inner_circle' | 'family';
  clearance_categories?: string[];
  clearance_expires_at?: number;
  clearance_field_grants?: string[];
  clearance_field_denials?: string[];
  // Tags
  tags?: string[];
}

interface NetworkGraphProps {
  relationships: Relationship[];
  centerQube: Qube;
  allQubes: Qube[];
  onNodeClick?: (entityId: string) => void;
}

// Helper functions for localStorage
const getStorageKey = (qubeId: string) => `network-view-${qubeId}`;

const saveViewportToStorage = (qubeId: string, viewport: Viewport) => {
  try {
    localStorage.setItem(getStorageKey(qubeId), JSON.stringify(viewport));
  } catch (error) {
    console.warn('Failed to save viewport to localStorage:', error);
  }
};

const loadViewportFromStorage = (qubeId: string): Viewport | null => {
  try {
    const stored = localStorage.getItem(getStorageKey(qubeId));
    return stored ? JSON.parse(stored) : null;
  } catch (error) {
    console.warn('Failed to load viewport from localStorage:', error);
    return null;
  }
};

const saveNodePositionsToStorage = (qubeId: string, nodes: Node[]) => {
  try {
    const positions = nodes.reduce((acc, node) => {
      acc[node.id] = node.position;
      return acc;
    }, {} as Record<string, { x: number; y: number }>);
    localStorage.setItem(`${getStorageKey(qubeId)}-positions`, JSON.stringify(positions));
  } catch (error) {
    console.warn('Failed to save node positions to localStorage:', error);
  }
};

const loadNodePositionsFromStorage = (qubeId: string): Record<string, { x: number; y: number }> | null => {
  try {
    const stored = localStorage.getItem(`${getStorageKey(qubeId)}-positions`);
    return stored ? JSON.parse(stored) : null;
  } catch (error) {
    console.warn('Failed to load node positions from localStorage:', error);
    return null;
  }
};

// Internal component that uses ReactFlow context
const NetworkGraphInner: React.FC<NetworkGraphProps> = ({
  relationships,
  centerQube,
  allQubes,
  onNodeClick,
}) => {
  const reactFlowInstance = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const savedPositionsRef = useRef<Record<string, { x: number; y: number }> | null>(null);

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'best_friend': return '#ff69b4';
      case 'close_friend': return '#ff1493';
      case 'friend': return '#00ff88';
      case 'acquaintance': return '#ffaa00';
      case 'stranger': return '#888888';
      case 'unmet': return '#666666';
      case 'suspicious': return '#ff8800';
      case 'rival': return '#ff6600';
      case 'enemy': return '#ff3333';
      case 'blocked': return '#cc0000';
      default: return '#888888';
    }
  };

  const getTrustColor = (trust: number): string => {
    if (trust >= 75) return '#00ff88';
    if (trust >= 50) return '#ffaa00';
    if (trust >= 25) return '#ff8800';
    return '#ff3366';
  };

  const getNodeSize = (relationship: Relationship): { width: number; height: number } => {
    // Base size, scale up based on trust and friendship
    const trustFactor = relationship.trust / 100;
    const friendshipFactor = relationship.friendship / 100;
    const combinedFactor = (trustFactor + friendshipFactor) / 2;
    const baseWidth = 120;
    const baseHeight = 90;
    const scaleFactor = combinedFactor * 0.4; // 0-40% increase
    return {
      width: baseWidth + (baseWidth * scaleFactor),
      height: baseHeight + (baseHeight * scaleFactor)
    };
  };

  const getEdgeWidth = (relationship: Relationship): number => {
    // Base width 2, scale up based on interaction frequency
    const messageCount = relationship.messages_sent + relationship.messages_received;
    if (messageCount === 0) return 1;
    if (messageCount < 10) return 2;
    if (messageCount < 50) return 3;
    if (messageCount < 100) return 4;
    return 5;
  };

  const getStatusEmoji = (status: string): string => {
    switch (status) {
      case 'best_friend': return '💖';
      case 'close_friend': return '💕';
      case 'friend': return '💚';
      case 'acquaintance': return '👋';
      case 'stranger': return '🤝';
      case 'unmet': return '❓';
      default: return '🤝';
    }
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'best_friend': return 'Best Friend';
      case 'close_friend': return 'Close Friend';
      case 'friend': return 'Friend';
      case 'acquaintance': return 'Acquaintance';
      case 'stranger': return 'Stranger';
      case 'unmet': return 'Unmet';
      default: return 'Unknown';
    }
  };

  // Clearance profile border styles
  const getClearanceBorderStyle = (profile?: string): { border: string; boxShadow?: string } => {
    switch (profile) {
      case 'family':
        return { border: '3px solid #ff69b4', boxShadow: '0 0 8px #ff69b4, 0 0 16px #ff69b480' };
      case 'inner_circle':
        return { border: '3px solid #00ff88', boxShadow: '0 0 8px #00ff88, 0 0 16px #00ff8880' };
      case 'trusted':
        return { border: '3px solid #00cc66' };
      case 'social':
        return { border: '2px solid #ffaa00' };
      case 'professional':
        return { border: '2px solid #4a90e2' };
      case 'public':
        return { border: '2px solid #888888' };
      case 'none':
        return { border: '2px dashed #666666' };
      default:
        return { border: '2px solid #444444' };
    }
  };

  const getClearanceIcon = (profile?: string): string => {
    switch (profile) {
      case 'family': return '👨‍👩‍👧‍👦';
      case 'inner_circle': return '💫';
      case 'trusted': return '🔒';
      case 'social': return '🎉';
      case 'professional': return '💼';
      case 'public': return '🌐';
      case 'none': return '🚫';
      default: return '❓';
    }
  };

  const formatClearanceLabel = (profile?: string): string => {
    switch (profile) {
      case 'none': return 'None';
      case 'public': return 'Minimal';
      case 'professional': return 'Limited';
      case 'social': return 'Standard';
      case 'trusted': return 'Extended';
      case 'inner_circle': return 'Full';
      case 'family': return 'Complete';
      default: return 'None';
    }
  };

  // Calculate network stats
  const networkStats = useMemo(() => {
    if (!relationships || relationships.length === 0) return null;

    const totalTrust = relationships.reduce((sum, rel) => sum + rel.trust, 0);
    const totalMessages = relationships.reduce(
      (sum, rel) => sum + rel.messages_sent + rel.messages_received,
      0
    );
    const mostActive = relationships.reduce((max, rel) => {
      const count = rel.messages_sent + rel.messages_received;
      const maxCount = max.messages_sent + max.messages_received;
      return count > maxCount ? rel : max;
    });

    return {
      totalRelationships: relationships.length,
      avgTrust: Math.round(totalTrust / relationships.length),
      totalMessages,
      mostActiveRelationship: mostActive.entity_name || mostActive.entity_id,
      mostActiveCount: mostActive.messages_sent + mostActive.messages_received,
    };
  }, [relationships]);

  // Load saved positions when component mounts
  useEffect(() => {
    savedPositionsRef.current = loadNodePositionsFromStorage(centerQube.qube_id);
  }, [centerQube.qube_id]);

  // Restore viewport after nodes are initialized
  useEffect(() => {
    if (!isInitialized && nodes.length > 0 && reactFlowInstance) {
      const savedViewport = loadViewportFromStorage(centerQube.qube_id);
      if (savedViewport) {
        reactFlowInstance.setViewport(savedViewport);
      }
      setIsInitialized(true);
    }
  }, [nodes, isInitialized, reactFlowInstance, centerQube.qube_id]);

  useEffect(() => {
    if (!relationships || relationships.length === 0) {
      setNodes([]);
      setEdges([]);
      setIsInitialized(false);
      return;
    }

    // Load saved positions
    const savedPositions = savedPositionsRef.current;

    // Create center node for the selected qube
    const centerPosition = savedPositions?.[centerQube.qube_id] || { x: 320, y: 240 };
    const centerNode: Node = {
      id: centerQube.qube_id,
      type: 'default',
      position: centerPosition,
      className: 'network-node-center',
      data: {
        label: (
          <div className="text-center flex flex-col items-center">
            {centerQube.avatar_url ? (
              <img
                src={centerQube.avatar_url}
                alt={centerQube.name}
                className="w-16 h-16 rounded-full mb-1 object-cover"
                style={{ border: `2px solid ${centerQube.favorite_color}` }}
              />
            ) : (
              <div
                className="w-16 h-16 rounded-full mb-1 flex items-center justify-center text-2xl"
                style={{
                  background: `${centerQube.favorite_color}40`,
                  border: `2px solid ${centerQube.favorite_color}`
                }}
              >
                {centerQube.name[0]}
              </div>
            )}
            <div className="font-bold text-sm" style={{ color: centerQube.favorite_color }}>
              {centerQube.name}
            </div>
          </div>
        ),
      },
      style: {
        background: 'rgba(74, 144, 226, 0.2)',
        border: `3px solid ${centerQube.favorite_color}`,
        borderRadius: '16px',
        width: 160,
        height: 120,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '14px',
        color: '#fff',
        padding: '12px',
        ['--node-color' as any]: centerQube.favorite_color,
      },
      draggable: false,
    };

    // Create nodes for each relationship in a circle around center
    const radius = 250;
    const angleStep = (2 * Math.PI) / relationships.length;

    const relationshipNodes: Node[] = relationships.map((rel, index) => {
      const angle = index * angleStep;
      const x = 400 + radius * Math.cos(angle);
      const y = 300 + radius * Math.sin(angle);
      const { width, height } = getNodeSize(rel);

      // Find qube color if it's a qube
      const qube = allQubes.find(q => q.qube_id === rel.entity_id);
      const nodeColor = qube?.favorite_color || getTrustColor(rel.trust);

      const statusEmoji = getStatusEmoji(rel.status);
      const messageCount = rel.messages_sent + rel.messages_received;

      // Use saved position if available, otherwise use calculated circle position
      const defaultPosition = { x: x - width / 2, y: y - height / 2 };
      const savedPosition = savedPositions?.[rel.entity_id];
      const position = savedPosition || defaultPosition;

      // Get clearance border style
      const clearanceBorderStyle = getClearanceBorderStyle(rel.clearance_profile);

      // Get tags (show max 2)
      const tags = rel.tags || [];
      const displayTags = tags.slice(0, 2);
      const extraTagCount = tags.length - 2;

      return {
        id: rel.entity_id,
        type: 'default',
        position,
        className: 'network-node-relationship',
        data: {
          label: (
            <div className="text-center relative pt-2">
              {/* Status Badge - positioned above the name */}
              <div
                className="absolute -top-2 left-1/2 transform -translate-x-1/2 text-lg"
                title={getStatusLabel(rel.status)}
              >
                {statusEmoji}
              </div>

              <div
                className="font-semibold truncate mt-1"
                style={{ color: nodeColor }}
              >
                {rel.entity_name || rel.entity_id}
              </div>
              <div className="text-xs text-gray-400">
                Trust: {Math.round(rel.trust)}
              </div>

              {/* Tags Display */}
              {tags.length > 0 && (
                <div className="flex items-center justify-center gap-0.5 mt-1 flex-wrap">
                  {displayTags.map((tag, i) => (
                    <span
                      key={i}
                      className="px-1 py-0 text-[9px] bg-accent-secondary/30 text-accent-secondary rounded"
                      title={tag}
                    >
                      {tag.length > 6 ? tag.substring(0, 6) + '..' : tag}
                    </span>
                  ))}
                  {extraTagCount > 0 && (
                    <span className="text-[9px] text-gray-500">+{extraTagCount}</span>
                  )}
                </div>
              )}

              {/* Clearance Badge */}
              {rel.clearance_profile && rel.clearance_profile !== 'none' && (
                <div
                  className="mt-1 text-[9px] px-1.5 py-0.5 rounded-full inline-flex items-center gap-0.5"
                  style={{
                    background: getClearanceBorderStyle(rel.clearance_profile).border.includes('#')
                      ? getClearanceBorderStyle(rel.clearance_profile).border.split(' ').pop() + '30'
                      : '#44444430',
                    border: `1px solid ${getClearanceBorderStyle(rel.clearance_profile).border.split(' ').pop() || '#444'}`,
                  }}
                  title={`Clearance: ${formatClearanceLabel(rel.clearance_profile)}`}
                >
                  <span className="text-[8px]">{getClearanceIcon(rel.clearance_profile)}</span>
                  <span className="text-gray-300">{formatClearanceLabel(rel.clearance_profile)}</span>
                </div>
              )}
            </div>
          ),
          // Store relationship data for tooltip
          relationship: rel,
        },
        style: {
          background: hoveredNode === rel.entity_id
            ? `${getStatusColor(rel.status)}40`
            : `${getStatusColor(rel.status)}20`,
          ...clearanceBorderStyle,
          borderRadius: '12px',
          width: width,
          height: height + (tags.length > 0 ? 15 : 0) + (rel.clearance_profile && rel.clearance_profile !== 'none' ? 20 : 0),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          color: '#fff',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          padding: '8px',
          ['--node-color' as any]: getStatusColor(rel.status),
        },
        draggable: true,
      };
    });

    // Create edges from center to each relationship
    const relationshipEdges: Edge[] = relationships.map((rel) => {
      const messageCount = rel.messages_sent + rel.messages_received;

      return {
        id: `${centerQube.qube_id}-${rel.entity_id}`,
        source: centerQube.qube_id,
        target: rel.entity_id,
        type: 'default',
        animated: rel.interaction_frequency_per_day ? rel.interaction_frequency_per_day > 1 : false,
        label: messageCount > 0 ? `${messageCount}` : undefined,
        labelStyle: {
          fill: '#888',
          fontSize: 10,
          fontWeight: 600,
        },
        labelBgStyle: {
          fill: '#1a1a1a',
          fillOpacity: 0.8,
        },
        style: {
          stroke: getStatusColor(rel.status),
          strokeWidth: getEdgeWidth(rel),
          filter: hoveredNode === rel.entity_id
            ? `drop-shadow(0 0 6px ${getStatusColor(rel.status)}) drop-shadow(0 0 12px ${getStatusColor(rel.status)})`
            : 'none',
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: getStatusColor(rel.status),
          width: 15,
          height: 15,
        },
        data: {
          relationship: rel,
        },
      };
    });

    setNodes([centerNode, ...relationshipNodes]);
    setEdges(relationshipEdges);
  }, [relationships, centerQube, allQubes]);

  const onNodeClickHandler = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (node.id !== centerQube.qube_id && onNodeClick) {
        onNodeClick(node.id);
      }
    },
    [centerQube, onNodeClick]
  );

  // Save viewport when it changes
  const onMoveEnd = useCallback(() => {
    if (reactFlowInstance) {
      const viewport = reactFlowInstance.getViewport();
      saveViewportToStorage(centerQube.qube_id, viewport);
    }
  }, [reactFlowInstance, centerQube.qube_id]);

  // Save node positions when dragging stops
  const onNodeDragStop = useCallback(() => {
    saveNodePositionsToStorage(centerQube.qube_id, nodes);
  }, [nodes, centerQube.qube_id]);

  // Custom onNodesChange that also saves positions
  const handleNodesChange = useCallback((changes: any) => {
    onNodesChange(changes);
  }, [onNodesChange]);

  if (!relationships || relationships.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary">
        <div className="text-center">
          <div className="text-4xl mb-4">🌐</div>
          <p>No relationships to visualize</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-background-secondary rounded-lg overflow-hidden relative">
      <NetworkBackground />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClickHandler}
        onNodeDragStop={onNodeDragStop}
        onMoveEnd={onMoveEnd}
        fitView={!savedPositionsRef.current}
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
        onNodeMouseEnter={(_, node) => setHoveredNode(node.id)}
        onNodeMouseLeave={() => setHoveredNode(null)}
        style={{ background: 'transparent' }}
      >
        <Controls />

        {/* Stats Summary Panel */}
        {networkStats && (
          <Panel position="top-left">
            <div className="bg-glass-bg/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-glass-border min-w-[200px]">
              <h3 className="text-sm font-bold text-accent-primary mb-2">Network Stats</h3>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Relationships:</span>
                  <span className="text-text-primary font-semibold">{networkStats.totalRelationships}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Avg Trust:</span>
                  <span className="text-text-primary font-semibold">{networkStats.avgTrust}/100</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-tertiary">Total Messages:</span>
                  <span className="text-text-primary font-semibold">{networkStats.totalMessages}</span>
                </div>
                <div className="mt-2 pt-2 border-t border-glass-border">
                  <div className="text-text-tertiary">Most Active:</div>
                  <div className="text-accent-primary font-semibold truncate">
                    {networkStats.mostActiveRelationship}
                  </div>
                  <div className="text-text-tertiary text-xs">
                    {networkStats.mostActiveCount} messages
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        )}

        {/* Legend Panel */}
        <Panel position="bottom-right">
          <div className="bg-glass-bg/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-glass-border max-h-[400px] overflow-y-auto">
            <h3 className="text-sm font-bold text-accent-primary mb-2">Legend</h3>
            <div className="space-y-2 text-xs">
              {/* Node Size */}
              <div>
                <div className="font-semibold text-text-secondary mb-1">Node Size</div>
                <div className="text-text-tertiary">Trust + Friendship</div>
              </div>

              {/* Edge Width */}
              <div>
                <div className="font-semibold text-text-secondary mb-1">Connection Width</div>
                <div className="text-text-tertiary">Message Count</div>
              </div>

              {/* Clearance Borders */}
              <div>
                <div className="font-semibold text-text-secondary mb-1">Clearance (Border)</div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #ff69b4', boxShadow: '0 0 4px #ff69b4' }}></div>
                    <span className="text-text-tertiary">👨‍👩‍👧‍👦 Complete</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #00ff88', boxShadow: '0 0 4px #00ff88' }}></div>
                    <span className="text-text-tertiary">💫 Full</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #00cc66' }}></div>
                    <span className="text-text-tertiary">🔒 Extended</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #ffaa00' }}></div>
                    <span className="text-text-tertiary">🎉 Standard</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #4a90e2' }}></div>
                    <span className="text-text-tertiary">💼 Limited</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px solid #888' }}></div>
                    <span className="text-text-tertiary">🌐 Minimal</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-3 rounded" style={{ border: '2px dashed #666' }}></div>
                    <span className="text-text-tertiary">🚫 None</span>
                  </div>
                </div>
              </div>

              {/* Status Colors */}
              <div>
                <div className="font-semibold text-text-secondary mb-1">Status (Background)</div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#ff69b4' }}></div>
                    <span className="text-text-tertiary">💖 Best Friend</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#ff1493' }}></div>
                    <span className="text-text-tertiary">💕 Close Friend</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#00ff88' }}></div>
                    <span className="text-text-tertiary">💚 Friend</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#ffaa00' }}></div>
                    <span className="text-text-tertiary">👋 Acquaintance</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ background: '#888888' }}></div>
                    <span className="text-text-tertiary">🤝 Stranger</span>
                  </div>
                </div>
              </div>

              {/* Animation */}
              <div>
                <div className="font-semibold text-text-secondary mb-1">Animated Lines</div>
                <div className="text-text-tertiary">High Activity (&gt;1/day)</div>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

// Wrapper component with ReactFlowProvider
export const NetworkGraph: React.FC<NetworkGraphProps> = (props) => {
  return (
    <ReactFlowProvider>
      <NetworkGraphInner {...props} />
    </ReactFlowProvider>
  );
};
