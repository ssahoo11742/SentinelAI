import { useState, useRef } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, X, FileUp } from 'lucide-react';
import { parseCSV } from '@/utils/csvParser';
import { Market } from '@/types/market';
import { useToast } from '@/hooks/use-toast';
import { Input } from '@/components/ui/input';

interface CSVUploaderProps {
  onDataLoaded: (markets: Market[]) => void;
}

export const CSVUploader = ({ onDataLoaded }: CSVUploaderProps) => {
  const [csvText, setCsvText] = useState('');
  const [isVisible, setIsVisible] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setCsvText(text);
      handleParse(text);
    };
    reader.readAsText(file);
  };

  const handleParse = (text?: string) => {
    const dataToProcess = text || csvText;
    try {
      const markets = parseCSV(dataToProcess);
      if (markets.length === 0) {
        toast({
          title: "Error parsing CSV",
          description: "No valid data found. Please check your CSV format.",
          variant: "destructive",
        });
        return;
      }
      
      onDataLoaded(markets);
      setIsVisible(false);
      toast({
        title: "Data loaded successfully",
        description: `${markets.length} markets loaded`,
      });
    } catch (error) {
      toast({
        title: "Error parsing CSV",
        description: "Please check your CSV format and try again.",
        variant: "destructive",
      });
    }
  };

  if (!isVisible) {
    return (
      <Button
        onClick={() => setIsVisible(true)}
        variant="outline"
        className="fixed bottom-6 right-6 shadow-lg"
      >
        <Upload className="w-4 h-4 mr-2" />
        Load New Data
      </Button>
    );
  }

  return (
    <Card className="border-border/50">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Load Market Data</CardTitle>
            <CardDescription>
              Paste your CSV data below to analyze prediction markets
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsVisible(false)}
            className="h-8 w-8"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            className="hidden"
          />
          <Button 
            onClick={() => fileInputRef.current?.click()} 
            variant="outline"
            className="flex-1"
          >
            <FileUp className="w-4 h-4 mr-2" />
            Upload CSV File
          </Button>
        </div>
        
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">Or paste data</span>
          </div>
        </div>

        <Textarea
          placeholder="Paste your CSV data here (including headers)..."
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          className="min-h-[200px] font-mono text-xs"
        />
        <div className="flex gap-2">
          <Button onClick={() => handleParse()} className="flex-1">
            <Upload className="w-4 h-4 mr-2" />
            Parse & Load Data
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setCsvText('')}
          >
            Clear
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
