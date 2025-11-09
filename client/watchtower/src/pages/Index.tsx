import { useState, useMemo, useEffect } from 'react';
import { Market } from '@/types/market';
import { MarketCard } from '@/components/MarketCard';
import { StatsCard } from '@/components/StatsCard';
import { FilterBar } from '@/components/FilterBar';
import { StatisticsCharts } from '@/components/StatisticsCharts';
import { TrendingUp, Target, AlertCircle, BarChart3, Shield } from 'lucide-react';
import { getRecommendationType } from '@/utils/csvParser';
import Papa from 'papaparse';
import { CustomJobForm } from '@/components/CustomJob';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const SUPABASE_URL = "https://uxrdywchpcwljsteomtn.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4cmR5d2NocGN3bGpzdGVvbXRuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjEyMDUzMywiZXhwIjoyMDc3Njk2NTMzfQ.jaQvrFqm4wTOyS_XxaUzCM1REtEyh-9Sj1EDFNjKJ8g";
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

const POLL_INTERVAL = 5000; // 5 seconds

const Index = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [initialLoading, setInitialLoading] = useState(true);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

const fetchLatestReport = async (isInitial = false) => {
  if (isInitial) setInitialLoading(true);
  try {
    // Step 1: Fetch completed jobs directly from Supabase
    const { data: jobs, error } = await supabase
      .from('pipeline_jobs')
      .select('*')
      .eq('status', 'completed')
      .not('storage_path', 'is', null)
      .order('created_at', { ascending: false })
      .limit(1);

    if (error) throw error;
    if (!jobs || jobs.length === 0) {
      setMarkets([]);
      if (isInitial) setInitialLoading(false);
      return;
    }

    const latest = jobs[0];

    // Step 2: Fetch CSV from Supabase storage
    const { data: csvData, error: storageError } = await supabase
      .storage
      .from('sentinel_reports')
      .download(latest.storage_path.replace('sentinel_reports/', ''));

    if (storageError) throw storageError;

    const csvText = await csvData.text();
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
    if (isInitial) setInitialLoading(false);
  }
};

  // initial fetch + polling
useEffect(() => {
  fetchLatestReport(true);
  const interval = setInterval(() => fetchLatestReport(false), POLL_INTERVAL);
  return () => clearInterval(interval);
}, []);


  // Calculate statistics
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

  // Filter counts for filter buttons
  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = {
      all: markets.length,
    };

    markets.forEach(market => {
      const type = getRecommendationType(market.Recommendation);
      counts[type] = (counts[type] || 0) + 1;
    });

    return counts;
  }, [markets]);

  // Filtered markets
  const filteredMarkets = useMemo(() => {
    if (selectedFilter === 'all') return markets;
    
    return markets.filter(market => 
      getRecommendationType(market.Recommendation) === selectedFilter
    );
  }, [markets, selectedFilter]);

  return (
    <div className="min-h-screen bg-background relative">
      {/* Loading Overlay - Only on initial load */}
      {initialLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="text-white text-lg font-semibold">Loading markets...</div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-border/50 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Shield className="w-8 h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                Sentinel-AI
              </h1>
              <p className="text-sm text-muted-foreground">
                AI-powered market inefficiency detector
              </p>
            </div>
          </div>

          {/* Custom Job Form Button */}
          <CustomJobForm
            currentJobId={currentJobId}
            onJobStarted={(jobId) => {
              setCurrentJobId(jobId);
            }}
            onJobCompleted={() => {
              setCurrentJobId(null);
              fetchLatestReport(false);
            }}
          />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">

        {/* Stats Grid */}
        {markets.length > 0 && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatsCard
                title="Total Markets"
                value={stats.totalMarkets}
                icon={BarChart3}
                subtitle="Analyzed opportunities"
              />
              <StatsCard
                title="Avg Edge"
                value={stats.avgEdge}
                icon={TrendingUp}
                subtitle="Potential profit margin"
                trend="up"
              />
              <StatsCard
                title="High Confidence"
                value={stats.highConfidence}
                icon={Target}
                subtitle=">60% confidence"
              />
              <StatsCard
                title="Strong Buys"
                value={stats.strongBuys}
                icon={AlertCircle}
                subtitle="Highest conviction"
                trend="up"
              />
            </div>

            {/* Filters */}
            <FilterBar
              selectedFilter={selectedFilter}
              onFilterChange={setSelectedFilter}
              counts={filterCounts}
            />



            {/* Markets Grid */}
            <div>
              <div className="mb-4">
                <h2 className="text-xl font-semibold">
                  {selectedFilter === 'all' 
                    ? 'All Market Opportunities' 
                    : `${selectedFilter} Opportunities`}
                </h2>
                <p className="text-sm text-muted-foreground">
                  Showing {filteredMarkets.length} of {markets.length} markets
                </p>
              </div>
              
              {filteredMarkets.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredMarkets.map((market) => (
                    <MarketCard key={market.Rank} market={market} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    No markets found with the selected filter
                  </p>
                </div>
              )}
            </div>
          </>
        )}
                    {/* Statistics Charts */}
            <StatisticsCharts markets={markets} />

        {/* Empty State */}
        {markets.length === 0 && !initialLoading && (
          <div className="text-center py-12">
            <Target className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-xl font-semibold mb-2">No Data Loaded</h3>
            <p className="text-muted-foreground">
              Run a custom job to get started with market analysis
            </p>
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
