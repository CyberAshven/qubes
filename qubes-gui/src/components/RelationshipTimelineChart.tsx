import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface RelationshipTimelineChartProps {
  data: {
    date: string;
    trust: number;
    compatibility: number;
  }[];
  color?: string;
}

export const RelationshipTimelineChart: React.FC<RelationshipTimelineChartProps> = ({
  data,
  color = '#4A90E2',
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-text-tertiary text-xs">
        <div className="text-center">
          <div className="text-2xl mb-2">📊</div>
          <p>No timeline data available</p>
        </div>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#888', fontSize: 10 }}
          stroke="#666"
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: '#888', fontSize: 10 }}
          stroke="#666"
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '8px',
            fontSize: '11px',
          }}
          labelStyle={{ color: '#fff', fontWeight: 'bold' }}
          itemStyle={{ color: '#fff' }}
        />
        <Legend
          wrapperStyle={{ fontSize: '11px' }}
          iconType="line"
        />
        <Line
          type="monotone"
          dataKey="trust"
          stroke="#4CAF50"
          strokeWidth={2}
          dot={{ fill: '#4CAF50', r: 3 }}
          name="Trust"
          activeDot={{ r: 5 }}
        />
        <Line
          type="monotone"
          dataKey="compatibility"
          stroke="#00aaff"
          strokeWidth={2}
          dot={{ fill: '#00aaff', r: 3 }}
          name="Compatibility"
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};
