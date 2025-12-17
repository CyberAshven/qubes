import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { QubeAvatarData } from '../../types';

interface AvatarNodeProps {
  data: QubeAvatarData;
}

export const AvatarNode = memo(({ data }: AvatarNodeProps) => {
  const { name, avatarUrl, favoriteColor } = data;

  return (
    <div
      className="relative w-[800px] h-[800px] rounded-full flex items-center justify-center"
      style={{
        background: `radial-gradient(circle, ${favoriteColor}40, ${favoriteColor}10)`,
        border: `10px solid ${favoriteColor}`,
        boxShadow: `0 0 120px ${favoriteColor}80, 0 0 200px ${favoriteColor}40`,
      }}
    >
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

      {/* Name label */}
      <div className="absolute -bottom-24 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
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
