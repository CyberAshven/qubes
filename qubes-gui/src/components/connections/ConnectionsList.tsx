import { GlassCard } from '../glass';
import { Connection } from './ConnectionManager';

interface ConnectionsListProps {
  connections: Connection[];
  onlineQubes: string[];
}

export const ConnectionsList: React.FC<ConnectionsListProps> = ({
  connections,
  onlineQubes,
}) => {
  if (connections.length === 0) {
    return (
      <GlassCard className="p-6 text-center">
        <p className="text-text-secondary">No connections yet</p>
        <p className="text-sm text-text-tertiary mt-2">
          Use the Discover tab to find and connect with other Qubes.
        </p>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-3">
      {connections.map((connection) => {
        const isOnline = onlineQubes.includes(connection.commitment);

        return (
          <GlassCard key={connection.commitment} className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* Online indicator */}
                <div
                  className={`w-3 h-3 rounded-full ${
                    isOnline ? 'bg-accent-success animate-pulse' : 'bg-text-tertiary'
                  }`}
                  title={isOnline ? 'Online' : 'Offline'}
                />

                <div>
                  <h3 className="font-display text-lg text-text-primary">
                    {connection.name}
                  </h3>
                  <p className="text-sm text-text-tertiary font-mono">
                    {connection.commitment.substring(0, 16)}...
                  </p>
                </div>
              </div>

              <div className="text-right">
                <span className={`text-sm ${isOnline ? 'text-accent-success' : 'text-text-tertiary'}`}>
                  {isOnline ? 'Online' : 'Offline'}
                </span>
                <p className="text-xs text-text-tertiary">
                  Connected {new Date(connection.accepted_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </GlassCard>
        );
      })}
    </div>
  );
};
