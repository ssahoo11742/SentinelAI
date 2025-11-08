import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Filter } from 'lucide-react';

interface FilterBarProps {
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
  counts: Record<string, number>;
}

export const FilterBar = ({ selectedFilter, onFilterChange, counts }: FilterBarProps) => {
  const filters = [
    { id: 'all', label: 'All Markets', count: counts.all || 0 },
    { id: 'STRONG BUY YES', label: 'Strong Buy Yes', count: counts['STRONG BUY YES'] || 0 },
    { id: 'BUY YES', label: 'Buy Yes', count: counts['BUY YES'] || 0 },
    { id: 'STRONG BUY NO', label: 'Strong Buy No', count: counts['STRONG BUY NO'] || 0 },
    { id: 'BUY NO', label: 'Buy No', count: counts['BUY NO'] || 0 },
    { id: 'MODERATE', label: 'Moderate', count: counts['MODERATE'] || 0 },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Filter className="w-4 h-4" />
        <span>Filter by Recommendation</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {filters.map((filter) => (
          <Button
            key={filter.id}
            variant={selectedFilter === filter.id ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange(filter.id)}
            className="gap-2"
          >
            {filter.label}
            <Badge 
              variant="secondary" 
              className="ml-1 px-1.5 py-0 text-xs"
            >
              {filter.count}
            </Badge>
          </Button>
        ))}
      </div>
    </div>
  );
};
