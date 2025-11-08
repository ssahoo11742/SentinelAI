import { useState, useMemo, useEffect } from 'react';
import { Market } from '@/types/market';
import { MarketCard } from '@/components/MarketCard';
import { StatsCard } from '@/components/StatsCard';
import { FilterBar } from '@/components/FilterBar';
import { StatisticsCharts } from '@/components/StatisticsCharts';
import { TrendingUp, Target, AlertCircle, BarChart3 } from 'lucide-react';
import { getRecommendationType } from '@/utils/csvParser';
import Papa from 'papaparse';
import { CustomJobForm } from '@/components/CustomJob';

const POLL_INTERVAL = 5000; // 5 seconds

const Index = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [refreshTrigger, setRefreshTrigger] = useState(0); // to trigger polling after job finishes

  const fetchLatestReport = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/jobs");
      const jobs = await res.json();

      const latest = jobs.find((j: any) => j.status === "completed" && j.storage_path);
      if (!latest) {
        setMarkets([]);
        setLoading(false);
        return;
      }

      const publicUrl = `https://uxrdywchpcwljsteomtn.supabase.co/storage/v1/object/public/${latest.storage_path}`;
      const csvResponse = await fetch(publicUrl);
      const csvText = await csvResponse.text();

      const parsed = Papa.parse(csvText, { header: true });
      const parsedMarkets = (parsed.data as Market[])
        .filter(m => m.Edge != null && !isNaN(m.Edge))
        .map(m => ({
          ...m,
          Edge: parseFloat(m.Edge as any),
          Confidence: parseFloat(m.Confidence as any),
          Kelly_Fraction: parseFloat(m.Kelly_Fraction as any),
          Model_Estimate: parseFloat(m.Model_Estimate as any),
          Market_Price: parseFloat(m.Market_Price as any)
        }));

      setMarkets(parsedMarkets);
    } catch (err) {
      console.error("Error loading latest report:", err);
    } finally {
      setLoading(false);
    }
  };

  // initial fetch + polling
  useEffect(() => {
    fetchLatestReport();
    const interval = setInterval(fetchLatestReport, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refreshTrigger]);

  // Statistics calculation
  const stats = useMemo(() => {
    const totalMarkets = markets.length;
    const avgEdge = markets.reduce((sum, m) => sum + m.Edge, 0) / totalMarkets || 0;
    const highConfidence = markets.filter(m => m.Confidence > 0.6).length;
    const strongBuys = markets.filter(m => 
      getRecommendationType(m.Recommendation).includes('STRONG BUY')
    ).length;

    return {
      totalMarkets,
      avgEdge: (avgEdge * 100).toFixed(1) + '%',
      highConfidence,
      strongBuys,
    };
  }, [markets]);

  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = { all: markets.length };
    markets.forEach(market => {
      const type = getRecommendationType(market.Recommendation);
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  }, [markets]);

  const filteredMarkets = useMemo(() => {
    if (selectedFilter === 'all') return markets;
    return markets.filter(market => getRecommendationType(market.Recommendation) === selectedFilter);
  }, [markets, selectedFilter]);

  return (
    <div className="min-h-screen bg-background relative">
      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="text-white text-lg font-semibold">Loading markets...</div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Target className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Prediction Market Dashboard</h1>
              <p className="text-sm text-muted-foreground">
                AI-powered market inefficiency detector
              </p>
            </div>
          </div>

          {/* Custom Job Form Button */}
          <CustomJobForm
            onJobStarted={(jobId) => {
              console.log("Started job:", jobId);
              // trigger refresh/polling immediately after job start
              setRefreshTrigger(prev => prev + 1);
            }}
          />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">
        {/* Stats Grid */}
        {markets.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatsCard title="Total Markets" value={stats.totalMarkets} icon={BarChart3} subtitle="Analyzed opportunities" />
              <StatsCard title="Avg Edge" value={stats.avgEdge} icon={TrendingUp} subtitle="Potential profit margin" trend="up" />
              <StatsCard title="High Confidence" value={stats.highConfidence} icon={Target} subtitle=">60% confidence" />
              <StatsCard title="Strong Buys" value={stats.strongBuys} icon={AlertCircle} subtitle="Highest conviction" trend="up" />
            </div>

            {/* Filters */}
            <FilterBar selectedFilter={selectedFilter} onFilterChange={setSelectedFilter} counts={filterCounts} />

            {/* Markets Grid */}
            <div>
              <div className="mb-4">
                <h2 className="text-xl font-semibold">
                  {selectedFilter === 'all' ? 'All Market Opportunities' : `${selectedFilter} Opportunities`}
                </h2>
                <p className="text-sm text-muted-foreground">
                  Showing {filteredMarkets.length} of {markets.length} markets
                </p>
              </div>
              
              {filteredMarkets.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredMarkets.map((market) => <MarketCard key={market.Rank} market={market} />)}
                </div>
              ) : (
                <div className="text-center py-12">
                  <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No markets found with the selected filter</p>
                </div>
              )}
              <StatisticsCharts markets={markets} />
            </div>
          </>
        )}

        {/* Empty State */}
        {markets.length === 0 && !loading && (
          <div className="text-center py-12">
            <Target className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-xl font-semibold mb-2">No Data Loaded</h3>
            <p className="text-muted-foreground">Paste your CSV data above to get started with market analysis</p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>⚠️ For educational purposes only. Always do your own research.</p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
