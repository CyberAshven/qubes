import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface RelationshipRadarChartProps {
  reliability: number;
  honesty: number;
  loyalty: number;
  respect: number;
  expertise: number;
  color?: string;
}

const CustomRadiusTick = (props: any) => {
  const { x, y, payload } = props;
  // Only show labels for 25, 50, 75
  if (payload.value === 0 || payload.value === 100) {
    return null;
  }
  return (
    <text x={x + 15} y={y} fill="#666" fontSize={9} textAnchor="start">
      {payload.value}
    </text>
  );
};

export const RelationshipRadarChart: React.FC<RelationshipRadarChartProps> = ({
  reliability,
  honesty,
  loyalty,
  respect,
  expertise,
  color = '#4A90E2',
}) => {
  const data = [
    {
      metric: 'Reliability',
      value: Math.round(reliability),
      fullMark: 100,
    },
    {
      metric: 'Honesty',
      value: Math.round(honesty),
      fullMark: 100,
    },
    {
      metric: 'Loyalty',
      value: Math.round(loyalty),
      fullMark: 100,
    },
    {
      metric: 'Respect',
      value: Math.round(respect),
      fullMark: 100,
    },
    {
      metric: 'Expertise',
      value: Math.round(expertise),
      fullMark: 100,
    },
  ];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="#333" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fill: '#888', fontSize: 11 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={<CustomRadiusTick />}
        />
        <Radar
          name="Relationship"
          dataKey="value"
          stroke={color}
          fill={color}
          fillOpacity={0.3}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
};
