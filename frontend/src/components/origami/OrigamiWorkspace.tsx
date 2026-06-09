"use client";

/**
 * OrigamiWorkspace — split-pane Origami surface, themed for the Bonito
 * dashboard. Lives inside (dashboard)/origami so it picks up the standard
 * auth + sidebar + PageHeader treatment.
 */

import { Activity, Boxes, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useOrigamiSession } from "./useOrigamiSession";
import { OrigamiChat } from "./OrigamiChat";
import { ResourcesGrid } from "./ResourcesGrid";
import { ActivityPanel } from "./ActivityPanel";
import { ProgressHeader } from "./ProgressHeader";
import { ResultPreview } from "./ResultPreview";

export function OrigamiWorkspace() {
  const session = useOrigamiSession();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 h-[calc(100vh-12rem)] min-h-[600px]">
      {/* Left: chat panel (2/5) — fixed height, internal scroll lives in OrigamiChat */}
      <Card className="lg:col-span-2 flex flex-col p-0 overflow-hidden h-full min-h-0">
        <OrigamiChat session={session} />
      </Card>

      {/* Right: workspace (3/5) — its OWN scrollable column so the chat
          can stay viewport-bounded while resources/activity scroll
          independently when there's a lot of either. */}
      <div className="lg:col-span-3 flex flex-col gap-4 h-full min-h-0 overflow-y-auto pr-1">
        <ProgressHeader execution={session.execution} />

        {/* Resources */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div className="flex items-center gap-2">
              <Boxes className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Resources</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              {session.resources.length} item
              {session.resources.length === 1 ? "" : "s"}
            </Badge>
          </CardHeader>
          <CardContent className="pt-0">
            <ResourcesGrid resources={session.resources} />
          </CardContent>
        </Card>

        {/* Result preview only when a deploy just finished */}
        {session.result && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-base">Result</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ResultPreview result={session.result} />
            </CardContent>
          </Card>
        )}

        {/* Activity log */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base">Activity log</CardTitle>
            </div>
            <Badge variant="outline" className="text-xs">
              {session.activity.length} call
              {session.activity.length === 1 ? "" : "s"}
            </Badge>
          </CardHeader>
          <CardContent className="pt-0">
            <ActivityPanel activity={session.activity} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
