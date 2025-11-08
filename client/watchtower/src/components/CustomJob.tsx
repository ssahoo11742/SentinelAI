import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Target, Clock, BarChart3 } from "lucide-react";

interface CustomJobFormProps {
  onJobStarted: (jobId: string) => void;
}

export const CustomJobForm = ({ onJobStarted }: CustomJobFormProps) => {
  const [open, setOpen] = useState(false);
  const [platforms, setPlatforms] = useState("manifold,polymarket");
  const [minLiquidity, setMinLiquidity] = useState(500);
  const [maxHours, setMaxHours] = useState(720);
  const [extraArgs, setExtraArgs] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        platforms: platforms.split(",").map((p) => p.trim()),
        min_liquidity: minLiquidity,
        max_hours: maxHours,
        extra_args: extraArgs.split(" ").filter((a) => a),
      };

      const res = await fetch("http://localhost:8000/custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      console.log("Custom job started:", data);
      onJobStarted(data.job_id);
      setOpen(false);
    } catch (err) {
      console.error("Failed to start job:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button onClick={() => setOpen(true)} variant="secondary">
        Run Custom Job
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Run Custom Pipeline</DialogTitle>
            <DialogDescription className="flex items-center gap-2">
              <Badge variant="outline" className="text-primary">
                Custom Configuration
              </Badge>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Platforms (comma-separated)</label>
              <Input value={platforms} onChange={(e) => setPlatforms(e.target.value)} />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Min Liquidity</label>
              <Input
                type="number"
                value={minLiquidity}
                onChange={(e) => setMinLiquidity(parseFloat(e.target.value))}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Max Hours</label>
              <Input
                type="number"
                value={maxHours}
                onChange={(e) => setMaxHours(parseFloat(e.target.value))}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Extra Args (space-separated)</label>
              <Input value={extraArgs} onChange={(e) => setExtraArgs(e.target.value)} />
            </div>

            <div className="flex gap-3 pt-2">
              <Button className="flex-1" onClick={handleSubmit} disabled={loading}>
                {loading ? "Starting..." : "Start Job"}
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setOpen(false)}>
                Cancel
              </Button>
            </div>

            <div className="text-xs text-muted-foreground text-center pt-2 border-t border-border/50">
              ⚠️ For educational purposes only. Always do your own research before running pipelines.
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
