import { useState } from 'react';
import { Market } from '@/types/market';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ExternalLink, TrendingUp, AlertCircle, Clock, Info } from 'lucide-react';
import { getRecommendationColor, getRecommendationType } from '@/utils/csvParser';
import { MarketDetailsModal } from './MarketDetailsModal';

interface MarketCardProps {
  market: Market;
}

export const MarketCard = ({ market }: MarketCardProps) => {
  const [showDetails, setShowDetails] = useState(false);
  const recommendationType = getRecommendationType(market.Recommendation);
  const colorClass = getRecommendationColor(market.Recommendation);

  return (
    <>
    <Card className="group hover:shadow-lg transition-all duration-300 border-border/50 hover:border-primary/30">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                #{market.Rank}
              </Badge>
              <Badge variant="secondary" className="text-xs capitalize">
                {market.Platform}
              </Badge>
            </div>
            <CardTitle className="text-base leading-tight group-hover:text-primary transition-colors">
              {market.Market_Question}
            </CardTitle>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Recommendation Badge */}
        <div className={`rounded-lg border px-3 py-2 text-sm font-medium ${colorClass}`}>
          {recommendationType}
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Edge</p>
            <p className="text-lg font-bold text-success">
              {(market.Edge * 100).toFixed(1)}%
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Confidence</p>
            <p className="text-lg font-bold">
              {(market.Confidence * 100).toFixed(1)}%
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Market Price</p>
            <p className="text-sm font-medium">
              {(market.Market_Price * 100).toFixed(1)}%
            </p>
          </div>
          
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Model Est.</p>
            <p className="text-sm font-medium">
              {(market.Model_Estimate * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Stats Row */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/50">
          <div className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            <span>{market.Num_Prob_Mentions} mentions</span>
          </div>
          <div className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            <span>{market.Num_Articles} articles</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{Math.floor(market.Hours_Until_Close / 24)}d</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDetails(true)}
            className="flex-1"
          >
            <Info className="w-3 h-3 mr-1" />
            Details
          </Button>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="flex-1"
          >
            <a
              href={market.Market_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              Open
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
    
    <MarketDetailsModal 
      market={market}
      open={showDetails}
      onOpenChange={setShowDetails}
    />
    </>
  );
};
