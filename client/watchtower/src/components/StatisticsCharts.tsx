import { useMemo } from 'react';
import { Market } from '@/types/market';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, LineChart, Line } from 'recharts';
import { getRecommendationType } from '@/utils/csvParser';

interface StatisticsChartsProps {
  markets: Market[];
}

export const StatisticsCharts = ({ markets }: StatisticsChartsProps) => {
  const chartData = useMemo(() => {
    // Recommendation distribution
    const recCounts: Record<string, number> = {};
    markets.forEach(m => {
      const type = getRecommendationType(m.Recommendation);
      recCounts[type] = (recCounts[type] || 0) + 1;
    });

    const recommendationData = Object.entries(recCounts).map(([name, value]) => ({
      name: name.replace('STRONG BUY ', '').replace('BUY ', ''),
      value,
      fullName: name
    }));

    // Edge distribution (buckets)
    const edgeBuckets = {
      '0-10%': 0,
      '10-20%': 0,
      '20-30%': 0,
      '30-40%': 0,
      '40%+': 0,
    };

    markets.forEach(m => {
      const edge = m.Edge * 100;
      if (edge < 10) edgeBuckets['0-10%']++;
      else if (edge < 20) edgeBuckets['10-20%']++;
      else if (edge < 30) edgeBuckets['20-30%']++;
      else if (edge < 40) edgeBuckets['30-40%']++;
      else edgeBuckets['40%+']++;
    });

    const edgeData = Object.entries(edgeBuckets).map(([name, count]) => ({
      edge: name,
      count
    }));

    // Confidence distribution
    const confidenceBuckets = {
      '0-20%': 0,
      '20-40%': 0,
      '40-60%': 0,
      '60-80%': 0,
      '80-100%': 0,
    };

    markets.forEach(m => {
      const conf = m.Confidence * 100;
      if (conf < 20) confidenceBuckets['0-20%']++;
      else if (conf < 40) confidenceBuckets['20-40%']++;
      else if (conf < 60) confidenceBuckets['40-60%']++;
      else if (conf < 80) confidenceBuckets['60-80%']++;
      else confidenceBuckets['80-100%']++;
    });

    const confidenceData = Object.entries(confidenceBuckets).map(([name, count]) => ({
      confidence: name,
      count
    }));

    // Top 10 markets by alpha score
    const topMarkets = [...markets]
      .sort((a, b) => b.Alpha_Score - a.Alpha_Score)
      .slice(0, 10)
      .map(m => ({
        question: m.Market_Question.slice(0, 30) + '...',
        alpha: (m.Alpha_Score * 100).toFixed(1),
        edge: (m.Edge * 100).toFixed(1)
      }));

    return {
      recommendationData,
      edgeData,
      confidenceData,
      topMarkets
    };
  }, [markets]);

  const COLORS = {
    'STRONG BUY YES': 'hsl(var(--success))',
    'BUY YES': 'hsl(var(--success) / 0.7)',
    'STRONG BUY NO': 'hsl(var(--danger))',
    'BUY NO': 'hsl(var(--danger) / 0.7)',
    'MODERATE': 'hsl(var(--warning))',
    'WEAK': 'hsl(var(--muted-foreground))',
    'UNKNOWN': 'hsl(var(--border))'
  };

  const getColor = (name: string) => {
    for (const [key, color] of Object.entries(COLORS)) {
      if (key.includes(name)) return color;
    }
    return COLORS.UNKNOWN;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-5">
      {/* Recommendation Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recommendation Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData.recommendationData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="hsl(var(--primary))"
                dataKey="value"
              >
                {chartData.recommendationData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getColor(entry.fullName)} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Edge Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Edge Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData.edgeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="edge" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Confidence Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Confidence Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData.confidenceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="confidence" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="count" fill="hsl(var(--chart-2))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Top Markets by Alpha Score */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Top 10 Markets by Alpha Score</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData.topMarkets} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" />
              <YAxis dataKey="question" type="category" stroke="hsl(var(--muted-foreground))" width={100} fontSize={10} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Bar dataKey="alpha" name="Alpha Score" fill="hsl(var(--success))" radius={[0, 8, 8, 0]} />
              <Bar dataKey="edge" name="Edge" fill="hsl(var(--primary))" radius={[0, 8, 8, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};
