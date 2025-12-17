import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  ConnectionLineType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { invoke, convertFileSrc } from '@tauri-apps/api/core';
import { Qube, Skill, SkillCategory, SkillTreeNode } from '../../types';
import { GlassCard } from '../glass';
import { useQubeSelection } from '../../hooks/useQubeSelection';
import { AvatarNode } from '../skills/AvatarNode';
import { SunNode } from '../skills/SunNode';
import { PlanetNode } from '../skills/PlanetNode';
import { MoonNode } from '../skills/MoonNode';
import { SkillDetailsPanel } from '../skills/SkillDetailsPanel';
import { SKILL_CATEGORIES, generateSkillsForQube } from '../../data/skillDefinitions';
import { useAuth } from '../../hooks/useAuth';

interface SkillsTabProps {
  qubes: Qube[];
}

// Calculate orbital positions for nodes
const calculateOrbitalPosition = (
  centerX: number,
  centerY: number,
  radius: number,
  angle: number
): { x: number; y: number } => {
  return {
    x: centerX + radius * Math.cos(angle),
    y: centerY + radius * Math.sin(angle),
  };
};

// Generate nodes and edges for the skill tree
const generateSkillTree = (qube: Qube, skills: Skill[], avatarUrl: string | undefined): { nodes: Node[]; edges: Edge[] } => {
  const centerX = 0;
  const centerY = 0;

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Add avatar node at center (very large)
  nodes.push({
    id: 'avatar',
    type: 'avatar',
    position: { x: centerX - 400, y: centerY - 400 }, // Center the 800x800 avatar
    data: {
      qubeId: qube.qube_id,
      name: qube.name,
      avatarUrl: avatarUrl,  // Use the computed avatar URL (IPFS or local via convertFileSrc)
      favoriteColor: qube.favorite_color,
    },
    draggable: false,
  });

  // Add Sun nodes (major categories) with collision avoidance
  const sunSkills = skills.filter((s) => s.nodeType === 'sun');
  const sunAngleStep = (2 * Math.PI) / sunSkills.length;

  // Store sun positions for planet calculations
  const sunPositions: Record<string, { x: number; y: number; angle: number; radius: number }> = {};
  const minSunDistance = 1200; // Minimum distance between sun centers (considering their solar systems)

  sunSkills.forEach((skill, index) => {
    let radius = 900 + Math.random() * 1600; // Random between 900-2500px
    const angleVariation = (Math.random() - 0.5) * 0.4; // ±0.2 radians variation
    const angle = index * sunAngleStep + angleVariation;
    let position = calculateOrbitalPosition(centerX, centerY, radius, angle);

    // Check distance to all previously placed suns
    let attempts = 0;
    let tooClose = true;
    while (tooClose && attempts < 10) {
      tooClose = false;
      for (const existingSunId in sunPositions) {
        const existingSun = sunPositions[existingSunId];
        const dx = position.x - existingSun.x;
        const dy = position.y - existingSun.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < minSunDistance) {
          tooClose = true;
          // Adjust radius: alternate between moving in and out
          if (attempts % 2 === 0) {
            radius += 300; // Move outward
          } else {
            radius -= 200; // Move inward
          }
          // Keep within bounds
          radius = Math.max(900, Math.min(2500, radius));
          position = calculateOrbitalPosition(centerX, centerY, radius, angle);
          break;
        }
      }
      attempts++;
    }

    // Store position for planet calculations
    sunPositions[skill.id] = { x: position.x, y: position.y, angle, radius };

    nodes.push({
      id: skill.id,
      type: 'sun',
      position: { x: position.x - 100, y: position.y - 100 }, // Center the 200x200 sun
      data: {
        skill,
        category: SKILL_CATEGORIES.find((c) => c.id === skill.category),
        orbitRadius: radius,
        orbitAngle: angle,
      },
      draggable: false,
    });

    // Connect sun to avatar (center to center, straight line)
    edges.push({
      id: `edge-avatar-${skill.id}`,
      source: 'avatar',
      target: skill.id,
      type: 'straight',
      animated: false,
      style: {
        stroke: SKILL_CATEGORIES.find((c) => c.id === skill.category)?.color || '#888',
        strokeWidth: 2,
        strokeDasharray: '5,5',
      },
    });
  });

  // Add Planet nodes (specific skills) with variation
  sunSkills.forEach((sunSkill) => {
    const planetSkills = skills.filter(
      (s) => s.nodeType === 'planet' && s.parentSkill === sunSkill.id
    );

    // Use stored sun position
    const sunPos = sunPositions[sunSkill.id];
    if (!sunPos) return; // Safety check

    const planetAngleStep = (2 * Math.PI) / planetSkills.length;

    planetSkills.forEach((skill, planetIndex) => {
      // Planets orbit sun: 300px to 500px range (increased minimum to account for larger suns)
      const planetRadius = 300 + Math.random() * 200; // Random between 300-500px
      const planetAngleVariation = (Math.random() - 0.5) * 0.8; // ±0.4 radians
      const angle = planetIndex * planetAngleStep + planetAngleVariation;
      const position = calculateOrbitalPosition(sunPos.x, sunPos.y, planetRadius, angle);

      nodes.push({
        id: skill.id,
        type: 'planet',
        position: { x: position.x - 30, y: position.y - 30 }, // Center the 60x60 planet
        data: {
          skill,
          category: SKILL_CATEGORIES.find((c) => c.id === skill.category),
          orbitRadius: planetRadius,
          orbitAngle: angle,
          orbitCenter: sunPos,
        },
        draggable: false,
      });

      // Connect planet to sun (center to center, straight line)
      edges.push({
        id: `edge-${sunSkill.id}-${skill.id}`,
        source: sunSkill.id,
        target: skill.id,
        type: 'straight',
        animated: skill.unlocked,
        style: {
          stroke: skill.unlocked ? SKILL_CATEGORIES.find((c) => c.id === skill.category)?.color || '#888' : '#444',
          strokeWidth: 1.5,
        },
      });

      // Add Moon nodes (sub-skills) with large variation
      const moonSkills = skills.filter(
        (s) => s.nodeType === 'moon' && s.parentSkill === skill.id
      );
      const moonAngleStep = (2 * Math.PI) / moonSkills.length;

      moonSkills.forEach((moonSkill, moonIndex) => {
        // Moons orbit planet: 50px to 120px range (clearly less than planet max of 400px)
        const moonRadius = 50 + Math.random() * 70; // Random between 50-120px
        const moonAngleVariation = (Math.random() - 0.5) * 1.0; // ±0.5 radians
        const moonAngle = moonIndex * moonAngleStep + moonAngleVariation;
        const moonPosition = calculateOrbitalPosition(position.x, position.y, moonRadius, moonAngle);

        nodes.push({
          id: moonSkill.id,
          type: 'moon',
          position: { x: moonPosition.x - 15, y: moonPosition.y - 15 }, // Center the 30x30 moon
          data: {
            skill: moonSkill,
            category: SKILL_CATEGORIES.find((c) => c.id === moonSkill.category),
            orbitRadius: moonRadius,
            orbitAngle: moonAngle,
            orbitCenter: position,
          },
          draggable: false,
        });

        // Connect moon to planet (center to center, straight line)
        edges.push({
          id: `edge-${skill.id}-${moonSkill.id}`,
          source: skill.id,
          target: moonSkill.id,
          type: 'straight',
          animated: moonSkill.unlocked,
          style: {
            stroke: moonSkill.unlocked ? SKILL_CATEGORIES.find((c) => c.id === moonSkill.category)?.color || '#888' : '#333',
            strokeWidth: 1,
          },
        });
      });
    });
  });

  return { nodes, edges };
};

// Custom node types
const nodeTypes = {
  avatar: AvatarNode,
  sun: SunNode,
  planet: PlanetNode,
  moon: MoonNode,
};

export const SkillsTab: React.FC<SkillsTabProps> = ({ qubes }) => {
  const { userId } = useAuth();
  const selectedQubeIds = useQubeSelection((state) => state.selectionByTab['skills']);
  const selectedQube = useMemo(() => {
    if (!selectedQubeIds || selectedQubeIds.length === 0) return null;
    return qubes.find((q) => selectedQubeIds[0] === q.qube_id) || null;
  }, [qubes, selectedQubeIds]);

  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBranchesExpanded, setIsBranchesExpanded] = useState(true);
  const [isToolsExpanded, setIsToolsExpanded] = useState(true);
  const [viewMode, setViewMode] = useState<'tree' | 'grid'>('tree');

  // Grid view filters and sorting
  const [filterStatus, setFilterStatus] = useState<'all' | 'unlocked' | 'locked'>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterNodeType, setFilterNodeType] = useState<'all' | 'sun' | 'planet' | 'moon'>('all');
  const [sortBy, setSortBy] = useState<'name' | 'level' | 'xp' | 'category'>('level');
  const [searchQuery, setSearchQuery] = useState('');

  // Dropdown open states
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [typeDropdownOpen, setTypeDropdownOpen] = useState(false);
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Helper function to get avatar URL (IPFS or local file via convertFileSrc)
  const getAvatarUrl = useCallback((qube: Qube): string | undefined => {
    // Priority 1: IPFS URL from backend
    if (qube.avatar_url) return qube.avatar_url;

    // Priority 2: Local file path via Tauri convertFileSrc
    if (qube.avatar_local_path) {
      return convertFileSrc(qube.avatar_local_path);
    }

    // Priority 3: Construct path from qube info (fallback for older qubes)
    if (userId && qube.name && qube.qube_id) {
      const projectRoot = 'C:/Users/bit_f/Projects/Qubes';
      const filePath = `${projectRoot}/data/users/${userId}/qubes/${qube.name}_${qube.qube_id}/chain/${qube.qube_id}_avatar.png`;
      return convertFileSrc(filePath);
    }

    return undefined;
  }, [userId]);

  // Calculate unlocked tools count
  const unlockedToolsCount = useMemo(() => {
    return skills.filter(s => s.unlocked && s.toolCallReward).length;
  }, [skills]);

  // Filtered and sorted skills for grid view
  const filteredAndSortedSkills = useMemo(() => {
    let filtered = [...skills];

    // Filter by status
    if (filterStatus === 'unlocked') {
      filtered = filtered.filter(s => s.unlocked);
    } else if (filterStatus === 'locked') {
      filtered = filtered.filter(s => !s.unlocked);
    }

    // Filter by category
    if (filterCategory !== 'all') {
      filtered = filtered.filter(s => s.category === filterCategory);
    }

    // Filter by node type
    if (filterNodeType !== 'all') {
      filtered = filtered.filter(s => s.nodeType === filterNodeType);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(s =>
        s.name.toLowerCase().includes(query) ||
        s.description.toLowerCase().includes(query) ||
        (s.toolCallReward && s.toolCallReward.toLowerCase().includes(query))
      );
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'level':
          return (b.level || 0) - (a.level || 0);
        case 'xp':
          return (b.currentXp || 0) - (a.currentXp || 0);
        case 'category':
          return a.category.localeCompare(b.category);
        default:
          return 0;
      }
    });

    return filtered;
  }, [skills, filterStatus, filterCategory, filterNodeType, sortBy, searchQuery]);

  // Load skills from backend when selected qube changes
  useEffect(() => {
    const loadSkills = async () => {
      if (!selectedQube || !userId) {
        setNodes([]);
        setEdges([]);
        setSkills([]);
        return;
      }

      setIsLoading(true);

      try {
        // Try to load skills from backend
        const response = await invoke<any>('get_qube_skills', {
          userId,
          qubeId: selectedQube.qube_id,
        });

        let loadedSkills: Skill[];

        // If no skills exist or empty, initialize with defaults
        if (!response.success || !response.skills || response.skills.length === 0) {
          console.log('No skills found, initializing defaults');
          loadedSkills = generateSkillsForQube(selectedQube.qube_id);

          // Save the initialized skills to backend
          await invoke('save_qube_skills', {
            userId,
            qubeId: selectedQube.qube_id,
            skillsJson: JSON.stringify({
              skills: loadedSkills,
              last_updated: new Date().toISOString(),
            }),
          });
        } else {
          loadedSkills = response.skills as Skill[];
        }

        // Generate visual tree
        const avatarUrl = getAvatarUrl(selectedQube);
        const { nodes: newNodes, edges: newEdges } = generateSkillTree(selectedQube, loadedSkills, avatarUrl);
        setSkills(loadedSkills);
        setNodes(newNodes);
        setEdges(newEdges);
      } catch (error) {
        console.error('Failed to load skills:', error);
        // Fallback to generated skills on error
        const fallbackSkills = generateSkillsForQube(selectedQube.qube_id);
        const avatarUrl = getAvatarUrl(selectedQube);
        const { nodes: newNodes, edges: newEdges } = generateSkillTree(selectedQube, fallbackSkills, avatarUrl);
        setSkills(fallbackSkills);
        setNodes(newNodes);
        setEdges(newEdges);
      } finally {
        setIsLoading(false);
      }
    };

    loadSkills();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedQube, userId, getAvatarUrl]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    if (node.type !== 'avatar') {
      setSelectedSkillId(node.id);
    }
  }, []);

  const selectedSkill = skills.find((s) => s.id === selectedSkillId);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.relative')) {
        setStatusDropdownOpen(false);
        setCategoryDropdownOpen(false);
        setTypeDropdownOpen(false);
        setSortDropdownOpen(false);
      }
    };

    if (statusDropdownOpen || categoryDropdownOpen || typeDropdownOpen || sortDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [statusDropdownOpen, categoryDropdownOpen, typeDropdownOpen, sortDropdownOpen]);

  // Reload skills when a skill is unlocked
  const handleSkillUnlocked = useCallback(async () => {
    if (!selectedQube || !userId) return;

    try {
      const response = await invoke<any>('get_qube_skills', {
        userId,
        qubeId: selectedQube.qube_id,
      });

      if (response.success && response.skills) {
        const loadedSkills = response.skills as Skill[];
        const avatarUrl = getAvatarUrl(selectedQube);
        const { nodes: newNodes, edges: newEdges } = generateSkillTree(selectedQube, loadedSkills, avatarUrl);
        setSkills(loadedSkills);
        setNodes(newNodes);
        setEdges(newEdges);
      }
    } catch (error) {
      console.error('Failed to reload skills:', error);
    }
  }, [selectedQube, userId, getAvatarUrl]);

  return (
    <div className="h-full flex flex-col">
      {/* View Toggle */}
      {selectedQube && (
        <div className="flex items-center justify-center gap-2 py-3 bg-bg-secondary border-b border-glass-border">
          <button
            onClick={() => setViewMode('tree')}
            className={`px-6 py-2 rounded-lg font-medium transition-all ${
              viewMode === 'tree'
                ? 'bg-accent-primary text-bg-primary shadow-lg shadow-accent-primary/30'
                : 'bg-glass-light text-text-secondary hover:bg-glass-border hover:text-text-primary'
            }`}
          >
            🌳 Tree View
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-6 py-2 rounded-lg font-medium transition-all ${
              viewMode === 'grid'
                ? 'bg-accent-primary text-bg-primary shadow-lg shadow-accent-primary/30'
                : 'bg-glass-light text-text-secondary hover:bg-glass-border hover:text-text-primary'
            }`}
          >
            📋 Grid View
          </button>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* React Flow Canvas or Grid View */}
        <div className="flex-1 relative">
          {!selectedQube ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <GlassCard className="p-8 text-center">
                <div className="text-6xl mb-4">🌟</div>
                <h2 className="text-2xl font-display text-accent-primary mb-2">Select a Qube</h2>
                <p className="text-text-secondary">
                  Choose a qube from the roster to view their skill tree
                </p>
              </GlassCard>
            </div>
          ) : viewMode === 'tree' ? (
          <>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.05}
              maxZoom={5}
              defaultViewport={{ x: 0, y: 0, zoom: 0.3 }}
              className="bg-bg-primary"
              proOptions={{ hideAttribution: true }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              connectionLineStyle={{ display: 'none' }}
              style={{
                background: `
                  radial-gradient(ellipse at 20% 30%, rgba(138, 43, 226, 0.15), transparent 40%),
                  radial-gradient(ellipse at 80% 70%, rgba(0, 119, 182, 0.15), transparent 40%),
                  radial-gradient(ellipse at 50% 50%, rgba(255, 0, 128, 0.08), transparent 50%),
                  radial-gradient(circle at 20% 30%, rgba(255,255,255,0.8) 0.5px, transparent 1px),
                  radial-gradient(circle at 60% 70%, rgba(255,255,255,0.6) 0.5px, transparent 1px),
                  radial-gradient(circle at 80% 10%, rgba(255,255,255,0.7) 0.5px, transparent 1px),
                  radial-gradient(circle at 90% 60%, rgba(255,255,255,0.5) 0.5px, transparent 1px),
                  radial-gradient(circle at 15% 85%, rgba(255,255,255,0.6) 0.5px, transparent 1px),
                  radial-gradient(circle at 65% 90%, rgba(255,255,255,0.4) 0.5px, transparent 1px),
                  radial-gradient(circle at 10% 60%, rgba(255,255,255,0.5) 0.5px, transparent 1px),
                  radial-gradient(circle at 95% 40%, rgba(255,255,255,0.6) 0.5px, transparent 1px),
                  #0a0e27
                `,
                backgroundSize: '100% 100%',
                backgroundPosition: '0% 0%',
              }}
            >
              <MiniMap
                style={{
                  backgroundColor: 'rgba(10, 14, 39, 0.8)',
                  border: '1px solid rgba(0, 255, 136, 0.2)',
                  borderRadius: '12px',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(0, 255, 136, 0.1)',
                  backdropFilter: 'blur(10px)',
                }}
                maskColor="rgba(10, 14, 39, 0.7)"
                nodeColor={(node) => {
                  if (node.type === 'avatar') return '#00ff88';
                  if (node.type === 'sun') {
                    const category = SKILL_CATEGORIES.find((c) => c.id === node.data.category?.id);
                    return category?.color || '#888';
                  }
                  if (node.type === 'planet') {
                    const category = SKILL_CATEGORIES.find((c) => c.id === node.data.category?.id);
                    return category?.color || '#666';
                  }
                  return '#444';
                }}
                nodeStrokeWidth={3}
                nodeBorderRadius={2}
              />
            </ReactFlow>

            {/* Branches Legend */}
            <div className="absolute top-4 left-4 z-10">
              <GlassCard className="p-4 space-y-2 w-[260px]">
                <h3
                  className="text-lg font-display text-accent-primary mb-3 flex items-center justify-between cursor-pointer"
                  onClick={() => setIsBranchesExpanded(!isBranchesExpanded)}
                >
                  <span>Branches</span>
                  <span className="text-sm transition-transform" style={{ transform: isBranchesExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
                </h3>
                {isBranchesExpanded && (
                  <div className="space-y-2">
                    {SKILL_CATEGORIES.map((category) => (
                      <div key={category.id} className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: category.color }}
                        />
                        <span className="text-sm text-text-primary">
                          {category.icon} {category.name}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </GlassCard>
            </div>

            {/* Tools Panel */}
            <div className="absolute bottom-4 left-4 z-10">
              <GlassCard className="p-4 space-y-2 w-[260px]">
                <h3
                  className="text-lg font-display text-accent-primary mb-3 flex items-center justify-between cursor-pointer"
                  onClick={() => setIsToolsExpanded(!isToolsExpanded)}
                >
                  <div className="flex items-center gap-2">
                    <span>🔓</span>
                    <span>Tools</span>
                    <span className="text-xs bg-accent-primary/20 text-accent-primary px-2 py-0.5 rounded-full">{unlockedToolsCount}</span>
                  </div>
                  <span className="text-sm transition-transform" style={{ transform: isToolsExpanded ? 'rotate(0deg)' : 'rotate(180deg)' }}>▼</span>
                </h3>
                {isToolsExpanded && (
                  <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar pr-2">
                    {/* Show unlocked skills with tool rewards */}
                    {skills
                      .filter(s => s.unlocked && s.toolCallReward)
                      .sort((a, b) => (b.level || 0) - (a.level || 0))
                      .map(skill => (
                        <div
                          key={skill.id}
                          className="flex items-center gap-2 p-2 rounded bg-glass-light border border-glass-border hover:border-accent-primary transition-colors cursor-pointer"
                          onClick={() => setSelectedSkillId(skill.id)}
                        >
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{
                              backgroundColor: SKILL_CATEGORIES.find(c => c.id === skill.category)?.color || '#888'
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-text-primary truncate">
                              {skill.name}
                            </div>
                            <div className="text-xs text-text-secondary">
                              Lvl {skill.level || 0} • {skill.toolCallReward}
                            </div>
                          </div>
                        </div>
                      ))
                    }
                    {skills.filter(s => s.unlocked && s.toolCallReward).length === 0 && (
                      <div className="text-sm text-text-secondary text-center py-4">
                        No tools unlocked yet.<br/>
                        Gain XP to unlock skills!
                      </div>
                    )}
                  </div>
                )}
              </GlassCard>
            </div>
          </>
          ) : (
            /* Grid View */
            <div className="h-full overflow-hidden flex flex-col bg-bg-primary">
              {/* Filter and Sort Controls */}
              <div className="p-4 bg-bg-secondary border-b border-glass-border space-y-3">
                {/* Search Bar */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder="🔍 Search skills..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-4 py-2 bg-bg-secondary border border-glass-border rounded-lg text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent-primary transition-colors"
                  />
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-2">
                  {/* Status Filter */}
                  <div className="relative">
                    <button
                      onClick={() => setStatusDropdownOpen(!statusDropdownOpen)}
                      className="px-3 py-1.5 bg-glass-light border border-glass-border rounded-lg text-sm text-text-primary hover:border-accent-primary transition-colors cursor-pointer flex items-center gap-2"
                    >
                      <span>{filterStatus === 'all' ? 'All Status' : filterStatus === 'unlocked' ? '🔓 Unlocked' : '🔒 Locked'}</span>
                      <span className="text-xs">▼</span>
                    </button>
                    {statusDropdownOpen && (
                      <div className="absolute top-full left-0 mt-1 bg-bg-secondary border border-glass-border rounded-lg shadow-lg z-50 min-w-full">
                        <button
                          onClick={() => { setFilterStatus('all'); setStatusDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          All Status
                        </button>
                        <button
                          onClick={() => { setFilterStatus('unlocked'); setStatusDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          🔓 Unlocked
                        </button>
                        <button
                          onClick={() => { setFilterStatus('locked'); setStatusDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          🔒 Locked
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Category Filter */}
                  <div className="relative">
                    <button
                      onClick={() => setCategoryDropdownOpen(!categoryDropdownOpen)}
                      className="px-3 py-1.5 bg-glass-light border border-glass-border rounded-lg text-sm text-text-primary hover:border-accent-primary transition-colors cursor-pointer flex items-center gap-2"
                    >
                      <span>{filterCategory === 'all' ? 'All Branches' : SKILL_CATEGORIES.find(c => c.id === filterCategory)?.name || 'All Branches'}</span>
                      <span className="text-xs">▼</span>
                    </button>
                    {categoryDropdownOpen && (
                      <div className="absolute top-full left-0 mt-1 bg-bg-secondary border border-glass-border rounded-lg shadow-lg z-50 min-w-full max-h-64 overflow-y-auto custom-scrollbar">
                        <button
                          onClick={() => { setFilterCategory('all'); setCategoryDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          All Branches
                        </button>
                        {SKILL_CATEGORIES.map((cat) => (
                          <button
                            key={cat.id}
                            onClick={() => { setFilterCategory(cat.id); setCategoryDropdownOpen(false); }}
                            className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors whitespace-nowrap"
                          >
                            {cat.icon} {cat.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Node Type Filter */}
                  <div className="relative">
                    <button
                      onClick={() => setTypeDropdownOpen(!typeDropdownOpen)}
                      className="px-3 py-1.5 bg-glass-light border border-glass-border rounded-lg text-sm text-text-primary hover:border-accent-primary transition-colors cursor-pointer flex items-center gap-2"
                    >
                      <span>{filterNodeType === 'all' ? 'All Types' : filterNodeType === 'sun' ? '🌟 Suns' : filterNodeType === 'planet' ? '🪐 Planets' : '🌙 Moons'}</span>
                      <span className="text-xs">▼</span>
                    </button>
                    {typeDropdownOpen && (
                      <div className="absolute top-full left-0 mt-1 bg-bg-secondary border border-glass-border rounded-lg shadow-lg z-50 min-w-full">
                        <button
                          onClick={() => { setFilterNodeType('all'); setTypeDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          All Types
                        </button>
                        <button
                          onClick={() => { setFilterNodeType('sun'); setTypeDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          🌟 Suns
                        </button>
                        <button
                          onClick={() => { setFilterNodeType('planet'); setTypeDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          🪐 Planets
                        </button>
                        <button
                          onClick={() => { setFilterNodeType('moon'); setTypeDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          🌙 Moons
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Sort */}
                  <div className="relative">
                    <button
                      onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
                      className="px-3 py-1.5 bg-glass-light border border-glass-border rounded-lg text-sm text-text-primary hover:border-accent-primary transition-colors cursor-pointer flex items-center gap-2"
                    >
                      <span>Sort: {sortBy === 'level' ? 'Level' : sortBy === 'name' ? 'Name' : sortBy === 'xp' ? 'XP' : 'Branch'}</span>
                      <span className="text-xs">▼</span>
                    </button>
                    {sortDropdownOpen && (
                      <div className="absolute top-full left-0 mt-1 bg-bg-secondary border border-glass-border rounded-lg shadow-lg z-50 min-w-full">
                        <button
                          onClick={() => { setSortBy('level'); setSortDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          Sort: Level
                        </button>
                        <button
                          onClick={() => { setSortBy('name'); setSortDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          Sort: Name
                        </button>
                        <button
                          onClick={() => { setSortBy('xp'); setSortDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          Sort: XP
                        </button>
                        <button
                          onClick={() => { setSortBy('category'); setSortDropdownOpen(false); }}
                          className="w-full px-3 py-2 text-left text-sm text-text-primary hover:bg-glass-light transition-colors"
                        >
                          Sort: Branch
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Results Count */}
                  <div className="ml-auto px-3 py-1.5 bg-glass-light border border-glass-border rounded-lg text-sm text-text-secondary">
                    {filteredAndSortedSkills.length} / {skills.length} skills
                  </div>
                </div>
              </div>

              {/* Skills Grid */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                {filteredAndSortedSkills.length === 0 ? (
                  /* Empty State */
                  <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <div className="text-6xl mb-4">🔍</div>
                      <h3 className="text-xl font-display text-text-primary mb-2">No skills found</h3>
                      <p className="text-text-secondary">
                        Try adjusting your filters or search query
                      </p>
                    </div>
                  </div>
                ) : (
                  /* Skills Grid - with optional dividers based on sort */
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filteredAndSortedSkills.map((skill, index) => {
                      const category = SKILL_CATEGORIES.find((c) => c.id === skill.category);
                      const parentSkill = skill.parentSkill ? skills.find((s) => s.id === skill.parentSkill) : null;
                      const xpProgress = skill.xpToNextLevel ? ((skill.currentXp || 0) / skill.xpToNextLevel) * 100 : 0;
                      const isSelected = selectedSkillId === skill.id;

                      // Check if we need a divider based on sort type
                      const prevSkill = index > 0 ? filteredAndSortedSkills[index - 1] : null;

                      // Category divider
                      const showCategoryDivider = sortBy === 'category' && prevSkill && prevSkill.category !== skill.category;

                      // Level divider - every 10 levels
                      const levelRange = Math.floor((skill.level || 0) / 10);
                      const prevLevelRange = prevSkill ? Math.floor((prevSkill.level || 0) / 10) : -1;
                      const showLevelDivider = sortBy === 'level' && levelRange !== prevLevelRange;
                      const levelRangeLabel = `Level ${levelRange * 10}-${levelRange * 10 + 9}`;

                      return (
                        <React.Fragment key={skill.id}>
                          {/* Category Divider */}
                          {showCategoryDivider && (
                            <div className="col-span-full flex items-center gap-3 mt-4 mb-2">
                              <h3 className="text-lg font-display text-accent-primary">
                                {category?.icon} {category?.name}
                              </h3>
                              <div className="flex-1 h-px bg-gradient-to-r from-glass-border to-transparent" />
                            </div>
                          )}

                          {/* Level Divider */}
                          {showLevelDivider && (
                            <div className="col-span-full flex items-center gap-3 mt-4 mb-2">
                              <h3 className="text-lg font-display text-accent-primary">
                                {levelRangeLabel}
                              </h3>
                              <div className="flex-1 h-px bg-gradient-to-r from-glass-border to-transparent" />
                            </div>
                          )}

                          {/* Skill Card */}
                          <GlassCard
                            className={`p-0 cursor-pointer transition-all overflow-hidden relative ${
                              isSelected
                                ? 'ring-4 scale-105'
                                : skill.unlocked
                                ? 'hover:shadow-lg hover:scale-102'
                                : ''
                            }`}
                            style={{
                              borderWidth: isSelected ? '3px' : '1px',
                              borderColor: isSelected ? category?.color || '#888' : 'rgba(255, 255, 255, 0.1)',
                              borderStyle: 'solid',
                              boxShadow: isSelected
                                ? `0 0 40px ${category?.color}80, 0 0 80px ${category?.color}40, inset 0 0 20px ${category?.color}20`
                                : undefined,
                              ringColor: category?.color || '#888',
                            }}
                            onClick={() => setSelectedSkillId(skill.id)}
                          >
                            {/* Lock Overlay - Only for locked skills */}
                            {!skill.unlocked && (
                              <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
                                <div className="text-[12rem] opacity-10">
                                  🔒
                                </div>
                              </div>
                            )}

                            {/* Colored Header Strip - at the top */}
                            <div
                              className="h-2 w-full"
                              style={{
                                background: `linear-gradient(90deg, ${category?.color || '#888'}00 0%, ${category?.color || '#888'} 50%, ${category?.color || '#888'}00 100%)`
                              }}
                            />

                            {/* Colored Left Border */}
                            <div className="flex">
                              <div
                                className="w-1"
                                style={{ backgroundColor: category?.color || '#888' }}
                              />

                              <div className="flex-1 p-4 relative">
                                {/* Dark header background - positioned lower to overlap with heading */}
                                <div
                                  className="absolute left-4 right-4 top-8 h-16 rounded-lg"
                                  style={{
                                    background: `linear-gradient(135deg, ${category?.color || '#888'}15 0%, ${category?.color || '#888'}05 100%)`
                                  }}
                                />

                                {/* Name and Icon - overlapping the dark bar */}
                                <div className="relative z-20 space-y-3">
                                  <div>
                                    <h3
                                      className="text-lg font-display mb-1 line-clamp-1"
                                      style={{ color: category?.color || '#888' }}
                                    >
                                      {skill.icon} {skill.name}
                                    </h3>
                                    <p className="text-xs text-text-secondary">
                                      {category?.name || 'Unknown'} • {skill.nodeType}
                                    </p>
                                  </div>

                                {/* Description */}
                                <p className="text-sm text-text-secondary line-clamp-2 min-h-[2.5rem]">
                                  {skill.description}
                                </p>

                                {/* Level and XP */}
                                <div>
                                  <div className="flex items-center justify-between text-sm mb-1">
                                    <span className="text-text-primary font-medium">
                                      Level {skill.level || 0}
                                    </span>
                                    <span className="text-text-secondary text-xs">
                                      {skill.currentXp || 0} / {skill.xpToNextLevel || 0} XP
                                    </span>
                                  </div>
                                  <div className="w-full h-2 bg-glass-light rounded-full overflow-hidden">
                                    <div
                                      className="h-full transition-all duration-300"
                                      style={{
                                        width: `${Math.min(xpProgress, 100)}%`,
                                        background: `linear-gradient(90deg, ${category?.color || '#888'}, ${category?.color || '#888'}cc)`
                                      }}
                                    />
                                  </div>
                                </div>

                                {/* Tool Reward */}
                                {skill.toolCallReward && (
                                  <div
                                    className="px-3 py-1.5 rounded-lg border"
                                    style={{
                                      backgroundColor: `${category?.color || '#888'}10`,
                                      borderColor: `${category?.color || '#888'}30`
                                    }}
                                  >
                                    <div className="text-xs font-medium" style={{ color: category?.color || '#888' }}>
                                      🛠️ Tool: {skill.toolCallReward}
                                    </div>
                                  </div>
                                )}

                                {/* Parent Skill */}
                                {parentSkill && (
                                  <div className="text-xs text-text-secondary">
                                    <span className="opacity-75">Parent:</span> {parentSkill.icon} {parentSkill.name}
                                  </div>
                                )}
                                </div>
                              </div>
                            </div>
                          </GlassCard>
                        </React.Fragment>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Skill Details Panel */}
        {selectedSkill && selectedQube && (
          <SkillDetailsPanel
            skill={selectedSkill}
            category={SKILL_CATEGORIES.find((c) => c.id === selectedSkill.category)}
            allSkills={skills}
            qubeId={selectedQube.qube_id}
            onClose={() => setSelectedSkillId(null)}
            onSkillUnlocked={handleSkillUnlocked}
          />
        )}
      </div>
    </div>
  );
};
