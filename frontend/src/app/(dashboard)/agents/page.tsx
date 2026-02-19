"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Bot, DollarSign, Activity, Calendar } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/auth";

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  budget_monthly: number | null;
  budget_spent: number;
  agent_count: number;
  created_at: string;
  updated_at: string;
}

interface CreateProjectData {
  name: string;
  description: string;
  budget_monthly?: number;
}

export default function AgentsOverviewPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();

  const [formData, setFormData] = useState<CreateProjectData>({
    name: "",
    description: "",
    budget_monthly: undefined,
  });

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const data = await apiRequest("/api/projects");
      setProjects(data);
    } catch (error) {
      console.error("Failed to fetch projects:", error);
      toast({
        title: "Error",
        description: "Failed to load projects",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);

    try {
      const projectData: CreateProjectData = {
        name: formData.name,
        description: formData.description || undefined,
        budget_monthly: formData.budget_monthly || undefined,
      };

      const newProject = await apiRequest("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectData),
      });

      setProjects([newProject, ...projects]);
      setCreateDialogOpen(false);
      setFormData({ name: "", description: "", budget_monthly: undefined });
      
      toast({
        title: "Success",
        description: "Project created successfully",
      });
    } catch (error) {
      console.error("Failed to create project:", error);
      toast({
        title: "Error",
        description: "Failed to create project",
        variant: "destructive",
      });
    } finally {
      setCreateLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Active</Badge>;
      case "paused":
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Paused</Badge>;
      case "archived":
        return <Badge className="bg-gray-500/10 text-gray-500 border-gray-500/20">Archived</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">AI Agents</h1>
            <p className="text-muted-foreground">Manage your enterprise AI agent projects</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="space-y-2">
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-16 bg-muted rounded"></div>
                <div className="flex justify-between">
                  <div className="h-4 bg-muted rounded w-20"></div>
                  <div className="h-4 bg-muted rounded w-16"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Agents</h1>
          <p className="text-muted-foreground">Manage your enterprise AI agent projects</p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Create a new project to organize your AI agents.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Project Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Customer Support Agents"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of this project..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="budget">Monthly Budget (USD)</Label>
                <Input
                  id="budget"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Optional monthly spend limit"
                  value={formData.budget_monthly || ""}
                  onChange={(e) => 
                    setFormData({ 
                      ...formData, 
                      budget_monthly: e.target.value ? parseFloat(e.target.value) : undefined 
                    })
                  }
                />
              </div>
              <div className="flex justify-end space-x-2">
                <Button type="button" variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createLoading}>
                  {createLoading ? "Creating..." : "Create Project"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {projects.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <Bot className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <CardTitle className="mb-2">No Projects Yet</CardTitle>
            <CardDescription className="mb-6">
              Create your first project to start building AI agents.
            </CardDescription>
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Your First Project
                </Button>
              </DialogTrigger>
            </Dialog>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Link key={project.id} href={`/agents/${project.id}`}>
              <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-blue-500/20">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{project.name}</CardTitle>
                      {getStatusBadge(project.status)}
                    </div>
                    <Bot className="h-5 w-5 text-blue-500" />
                  </div>
                  {project.description && (
                    <CardDescription className="line-clamp-2">
                      {project.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center text-muted-foreground">
                        <Activity className="mr-1 h-3 w-3" />
                        {project.agent_count} {project.agent_count === 1 ? "Agent" : "Agents"}
                      </div>
                      <div className="flex items-center text-muted-foreground">
                        <Calendar className="mr-1 h-3 w-3" />
                        {formatDate(project.created_at)}
                      </div>
                    </div>
                    
                    {project.budget_monthly && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">Monthly Spend</span>
                          <span className="font-medium">
                            {formatCurrency(project.budget_spent)} / {formatCurrency(project.budget_monthly)}
                          </span>
                        </div>
                        <div className="w-full bg-muted rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, (project.budget_spent / project.budget_monthly) * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}