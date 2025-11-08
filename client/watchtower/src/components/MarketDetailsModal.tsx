import { Market } from '@/types/market';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, TrendingUp, Target, Clock, BarChart3, Award, AlertCircle } from 'lucide-react';
import { getRecommendationColor } from '@/utils/csvParser';

interface MarketDetailsModalProps {
  market: Market | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const MarketDetailsModal = ({ market, open, onOpenChange }: MarketDetailsModalProps) => {
  if (!market) return null;

  const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
  const formatHours = (hours: number) => {
    if (hours < 24) return `${hours.toFixed(1)}h`;
    if (hours < 720) return `${(hours / 24).toFixed(1)} days`;
    return `${(hours / 720).toFixed(1)} months`;
  };

  const dataPoints = [
    {
      icon: TrendingUp,
      label: 'Market Price',
      value: formatPercent(market.Market_Price),
      description: 'Current market probability',
      color: 'text-primary'
    },
    {
      icon: Target,
      label: 'Model Estimate',
      value: formatPercent(market.Model_Estimate),
      description: 'AI model prediction',
      color: 'text-success'
    },
    {
      icon: BarChart3,
      label: 'Edge',
      value: formatPercent(market.Edge),
      description: 'Price vs model difference',
      color: 'text-warning'
    },
    {
      icon: Award,
      label: 'Alpha Score',
      value: formatPercent(market.Alpha_Score),
      description: 'Overall opportunity score',
      color: 'text-success'
    },
    {
      icon: AlertCircle,
      label: 'Confidence',
      value: formatPercent(market.Confidence),
      description: 'Model confidence level',
      color: 'text-primary'
    },
    {
      icon: Target,
      label: 'Kelly Fraction',
      value: formatPercent(market.Kelly_Fraction),
      description: 'Suggested position size',
      color: 'text-muted-foreground'
    },
  ];

  const metadata = [
    { label: 'Probability Mentions', value: market.Num_Prob_Mentions },
    { label: 'Articles Analyzed', value: market.Num_Articles },
    { label: 'Hours Until Close', value: formatHours(market.Hours_Until_Close) },
    { label: 'Validated', value: market.Validated },
    { label: 'Platform', value: market.Platform },
    { label: 'Rank', value: `#${market.Rank}` },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl pr-8">{market.Market_Question}</DialogTitle>
          <DialogDescription className="flex items-center gap-2 pt-2">
            <Badge variant="outline" className={getRecommendationColor(market.Recommendation)}>
              {market.Recommendation}
            </Badge>
            <span className="text-xs text-muted-foreground">Rank #{market.Rank}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 pt-4">
          {/* Key Metrics Grid */}
          <div>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
              Key Metrics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {dataPoints.map((point, index) => {
                const Icon = point.icon;
                return (
                  <div
                    key={index}
                    className="flex flex-col gap-2 p-4 rounded-lg border border-border/50 bg-card/50 hover:bg-card transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${point.color}`} />
                      <span className="text-xs text-muted-foreground">{point.label}</span>
                    </div>
                    <div className="text-2xl font-bold">{point.value}</div>
                    <div className="text-xs text-muted-foreground">{point.description}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Additional Metadata */}
          <div>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
              Market Details
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {metadata.map((item, index) => (
                <div key={index} className="flex flex-col gap-1 p-3 rounded-lg bg-muted/30">
                  <span className="text-xs text-muted-foreground">{item.label}</span>
                  <span className="text-sm font-semibold">{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis Summary */}
          <div className="p-4 rounded-lg border border-border/50 bg-card/50">
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground uppercase tracking-wide">
              Analysis Summary
            </h3>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Market inefficiency detected:</span>{' '}
                <span className="font-semibold">{formatPercent(market.Edge)}</span> edge between market price and model estimate.
              </p>
              <p>
                <span className="text-muted-foreground">Model confidence:</span>{' '}
                <span className="font-semibold">{formatPercent(market.Confidence)}</span> based on{' '}
                <span className="font-semibold">{market.Num_Articles}</span> articles with{' '}
                <span className="font-semibold">{market.Num_Prob_Mentions}</span> probability mentions.
              </p>
              <p>
                <span className="text-muted-foreground">Suggested position:</span>{' '}
                <span className="font-semibold">{formatPercent(market.Kelly_Fraction)}</span> of portfolio using Kelly Criterion.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button asChild className="flex-1">
              <a href={market.Market_URL} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Market on {market.Platform}
              </a>
            </Button>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>

          {/* Disclaimer */}
          <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border/50">
            ⚠️ For educational purposes only. Always do your own research before making any trading decisions.
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
