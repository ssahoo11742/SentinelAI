import { Market } from '@/types/market';

export const parseCSV = (csvText: string): Market[] => {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',');
  const markets: Market[] = [];

  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    if (values.length !== headers.length) continue;

    const market: Market = {
      Rank: parseInt(values[0]) || 0,
      Platform: values[1] || '',
      Market_Question: values[2] || '',
      Market_URL: values[3] || '',
      Market_Price: parseFloat(values[4]) || 0,
      Model_Estimate: parseFloat(values[5]) || 0,
      Edge: parseFloat(values[6]) || 0,
      Alpha_Score: parseFloat(values[7]) || 0,
      Confidence: parseFloat(values[8]) || 0,
      Kelly_Fraction: parseFloat(values[9]) || 0,
      Recommendation: values[10] || '',
      Num_Prob_Mentions: parseInt(values[11]) || 0,
      Num_Articles: parseInt(values[12]) || 0,
      Hours_Until_Close: parseFloat(values[13]) || 0,
      Validated: values[14] || '',
    };

    markets.push(market);
  }

  return markets;
};

// Handle CSV parsing with quoted fields
const parseCSVLine = (line: string): string[] => {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  
  result.push(current.trim());
  return result;
};

export const getRecommendationType = (recommendation: string | undefined): string => {
  const rec = recommendation?.toUpperCase() ?? "";

  if (rec.includes('STRONG BUY YES')) return 'STRONG BUY YES';
  if (rec.includes('BUY YES')) return 'BUY YES';
  if (rec.includes('STRONG BUY NO')) return 'STRONG BUY NO';
  if (rec.includes('BUY NO')) return 'BUY NO';
  if (rec.includes('MODERATE')) return 'MODERATE';
  if (rec.includes('WEAK')) return 'WEAK';
  
  return 'UNKNOWN';
};


export const getRecommendationColor = (recommendation: string): string => {
  const type = getRecommendationType(recommendation);
  
  switch (type) {
    case 'STRONG BUY YES':
      return 'text-success border-success/30 bg-success/10';
    case 'BUY YES':
      return 'text-success/80 border-success/20 bg-success/5';
    case 'STRONG BUY NO':
      return 'text-danger border-danger/30 bg-danger/10';
    case 'BUY NO':
      return 'text-danger/80 border-danger/20 bg-danger/5';
    case 'MODERATE':
      return 'text-warning border-warning/30 bg-warning/10';
    case 'WEAK':
      return 'text-neutral border-neutral/30 bg-neutral/10';
    default:
      return 'text-muted-foreground border-border/30 bg-muted/10';
  }
};
