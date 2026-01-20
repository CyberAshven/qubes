import { memo, useState, useCallback } from 'react';
import { Handle, Position } from '@xyflow/react';
import { QubeAvatarData } from '../../types';

interface AvatarNodeProps {
  data: QubeAvatarData & { totalXP?: number };
}

export const AvatarNode = memo(({ data }: AvatarNodeProps) => {
  const { name, avatarUrl, favoriteColor, totalXP } = data;
  const [showXP, setShowXP] = useState(false);
  const [fadeOut, setFadeOut] = useState(false);

  const handleAvatarClick = useCallback(() => {
    setShowXP(true);
    setFadeOut(false);

    // Start fade out after 4 seconds
    setTimeout(() => {
      setFadeOut(true);
    }, 4000);

    // Hide completely after 5 seconds
    setTimeout(() => {
      setShowXP(false);
      setFadeOut(false);
    }, 5000);
  }, []);

  return (
    <div
      className="relative w-[800px] h-[800px] rounded-full flex items-center justify-center cursor-pointer"
      style={{
        background: `radial-gradient(circle, ${favoriteColor}40, ${favoriteColor}10)`,
        border: `10px solid ${favoriteColor}`,
        boxShadow: `0 0 120px ${favoriteColor}80, 0 0 200px ${favoriteColor}40`,
      }}
      onClick={handleAvatarClick}
    >
      {/* Large XP display on click */}
      {showXP && (
        <div
          className={`absolute inset-0 flex items-center justify-center z-50 transition-opacity duration-1000 ${fadeOut ? 'opacity-0' : 'opacity-100'}`}
          style={{ pointerEvents: 'none' }}
        >
          <div
            className="text-[12rem] font-display font-bold flex items-center gap-6"
            style={{
              color: favoriteColor,
              textShadow: `0 0 60px ${favoriteColor}, 0 0 120px ${favoriteColor}80, 0 0 180px ${favoriteColor}60`,
            }}
          >
            <span>⭐</span>
            <span>{totalXP || 0}</span>
          </div>
        </div>
      )}

      {/* Avatar image */}
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt={name}
          className="w-full h-full rounded-full object-cover"
        />
      ) : (
        <div className="text-9xl font-bold" style={{ color: favoriteColor }}>
          {name.charAt(0)}
        </div>
      )}

      {/* Name label - moved down more */}
      <div className="absolute -bottom-32 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
        <div
          className="px-10 py-5 rounded-full text-6xl font-display font-bold"
          style={{
            backgroundColor: `${favoriteColor}20`,
            color: favoriteColor,
            border: `4px solid ${favoriteColor}60`,
            boxShadow: `0 0 25px ${favoriteColor}70, 0 0 50px ${favoriteColor}40`,
          }}
        >
          {name}
        </div>
      </div>

      {/* Center connection handle */}
      <Handle
        type="source"
        position={Position.Top}
        style={{
          opacity: 0,
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        }}
      />
    </div>
  );
});

AvatarNode.displayName = 'AvatarNode';
