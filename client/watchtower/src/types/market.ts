export interface Market {
  Rank: number;
  Platform: string;
  Market_Question: string;
  Market_URL: string;
  Market_Price: number;
  Model_Estimate: number;
  Edge: number;
  Alpha_Score: number;
  Confidence: number;
  Kelly_Fraction: number;
  Recommendation: string;
  Num_Prob_Mentions: number;
  Num_Articles: number;
  Hours_Until_Close: number;
  Validated: string;
}

export type RecommendationType = 'STRONG BUY YES' | 'BUY YES' | 'STRONG BUY NO' | 'BUY NO' | 'MODERATE' | 'WEAK';
