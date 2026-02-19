"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { 
  Plus, 
  Users, 
  Settings, 
  Database,
  Trash2,
  Edit,
  Shield,
  X
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

interface AgentGroup {
  id: string;
  name: string;
  description: string | null;
  knowledge_base_ids: string[];
  budget_limit: number | null;
  model_allowlist: string[];
  agent_count: number;
  created_at: string;
}

interface KnowledgeBase {
  id: string;
  name: string;
}

interface GroupManagementPanelProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onGroupChange?: () => void;
}

export function GroupManagementPanel({ 
  isOpen, 
  onClose, 
  projectId, 
  onGroupChange 
}: GroupManagementPanelProps) {
  const { toast } = useToast();
  const [groups, setGroups] = useState<AgentGroup[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<AgentGroup | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    knowledge_base_ids: [] as string[],
    budget_limit: "",
    model_allowlist: [] as string[],
  });

  useEffect(() => {
    if (isOpen && projectId) {
      fetchGroups();
      fetchKnowledgeBases();
    }
  }, [isOpen, projectId]);

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const res = await apiRequest(`/api/projects/${projectId}/groups`);
      if (res.ok) {
        const data = await res.json();
        setGroups(data);
      }
    } catch (error) {
      console.error("Failed to fetch groups:", error);
      toast({
        title: "Error",
        description: "Failed to load agent groups",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchKnowledgeBases = async () => {
    try {
      const res = await apiRequest("/api/knowledge-bases");
      if (res.ok) {
        const data = await res.json();
        setKnowledgeBases(data.items || []);
      }
    } catch (error) {
      console.error("Failed to fetch knowledge bases:", error);
    }
  };

  const handleCreateGroup = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Error",
        description: "Group name is required",
        variant: "destructive",
      });
      return;
    }

    try {
      const payload = {
        name: formData.name,
        description: formData.description || null,
        knowledge_base_ids: formData.knowledge_base_ids,
        budget_limit: formData.budget_limit ? parseFloat(formData.budget_limit) : null,
        model_allowlist: formData.model_allowlist,
      };

      const res = await apiRequest(`/api/projects/${projectId}/groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Agent group created successfully",
        });
        setIsCreating(false);
        resetForm();
        fetchGroups();
        onGroupChange?.();
      } else {
        const errorData = await res.json();
        toast({
          title: "Error",
          description: errorData.detail || "Failed to create group",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to create group:", error);
      toast({
        title: "Error",
        description: "Failed to create group",
        variant: "destructive",
      });
    }
  };

  const handleDeleteGroup = async (groupId: string) => {
    if (!confirm("Are you sure you want to delete this group? Agents in this group will remain but lose group association.")) {
      return;
    }

    try {
      const res = await apiRequest(`/api/groups/${groupId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Agent group deleted successfully",
        });
        fetchGroups();
        onGroupChange?.();
        setSelectedGroup(null);
      } else {
        toast({
          title: "Error",
          description: "Failed to delete group",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to delete group:", error);
      toast({
        title: "Error",
        description: "Failed to delete group",
        variant: "destructive",
      });
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      knowledge_base_ids: [],
      budget_limit: "",
      model_allowlist: [],
    });
  };

  const toggleKnowledgeBase = (kbId: string) => {
    setFormData(prev => ({
      ...prev,
      knowledge_base_ids: prev.knowledge_base_ids.includes(kbId)
        ? prev.knowledge_base_ids.filter(id => id !== kbId)
        : [...prev.knowledge_base_ids, kbId]
    }));
  };

  const addModel = (model: string) => {
    if (model && !formData.model_allowlist.includes(model)) {
      setFormData(prev => ({
        ...prev,
        model_allowlist: [...prev.model_allowlist, model]
      }));
    }
  };

  const removeModel = (model: string) => {
    setFormData(prev => ({
      ...prev,
      model_allowlist: prev.model_allowlist.filter(m => m !== model)
    }));
  };

  const models = ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "claude-3-haiku", "llama2-70b"];

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full max-w-2xl bg-[#1a1a2e] border-l border-gray-800 text-white overflow-y-auto">
        <SheetHeader className="pb-6">
          <SheetTitle className="text-white flex items-center">
            <Users className="h-5 w-5 mr-2" />
            Agent Groups
          </SheetTitle>
          <SheetDescription className="text-gray-400">
            Organize agents into departments with isolated knowledge bases and settings
          </SheetDescription>
        </SheetHeader>

        <Tabs defaultValue="groups" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 bg-[#2a2a4e]">
            <TabsTrigger value="groups" className="data-[state=active]:bg-blue-600">
              Groups
            </TabsTrigger>
            <TabsTrigger value="create" className="data-[state=active]:bg-blue-600">
              Create New
            </TabsTrigger>
          </TabsList>

          <TabsContent value="groups" className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                <span className="ml-3">Loading groups...</span>
              </div>
            ) : groups.length === 0 ? (
              <Card className="bg-[#2a2a4e] border-gray-700">
                <CardContent className="p-6 text-center">
                  <Users className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-lg font-medium mb-2">No groups yet</h3>
                  <p className="text-gray-400 mb-4">
                    Create your first agent group to organize your team's agents
                  </p>
                  <Button 
                    onClick={() => setIsCreating(true)}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Group
                  </Button>
                </CardContent>
              </Card>
            ) : (
              groups.map((group) => (
                <Card 
                  key={group.id} 
                  className="bg-[#2a2a4e] border-gray-700 cursor-pointer hover:border-blue-500 transition-colors"
                  onClick={() => setSelectedGroup(group)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{group.name}</CardTitle>
                      <div className="flex items-center space-x-2">
                        <Badge variant="secondary" className="bg-blue-600">
                          {group.agent_count} agents
                        </Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteGroup(group.id);
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {group.description && (
                      <p className="text-sm text-gray-400">{group.description}</p>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex items-center space-x-4 text-sm text-gray-400">
                      <div className="flex items-center">
                        <Database className="h-4 w-4 mr-1" />
                        {group.knowledge_base_ids.length} KBs
                      </div>
                      {group.budget_limit && (
                        <div className="flex items-center">
                          <Shield className="h-4 w-4 mr-1" />
                          ${group.budget_limit}/mo
                        </div>
                      )}
                      <div>
                        {new Date(group.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="create" className="space-y-6">
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Group Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., AdTech Team, Finance Department"
                  className="bg-[#2a2a4e] border-gray-600 text-white"
                />
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description of this group's purpose"
                  className="bg-[#2a2a4e] border-gray-600 text-white"
                />
              </div>

              <div>
                <Label>Knowledge Bases</Label>
                <div className="mt-2 space-y-2 max-h-32 overflow-y-auto">
                  {knowledgeBases.map((kb) => (
                    <div
                      key={kb.id}
                      className={`p-3 rounded cursor-pointer transition-colors ${
                        formData.knowledge_base_ids.includes(kb.id)
                          ? 'bg-blue-600 border-blue-500'
                          : 'bg-[#2a2a4e] border-gray-600 hover:border-gray-500'
                      } border`}
                      onClick={() => toggleKnowledgeBase(kb.id)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm">{kb.name}</span>
                        {formData.knowledge_base_ids.includes(kb.id) && (
                          <Badge variant="secondary" className="bg-blue-700 text-xs">
                            Selected
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                {knowledgeBases.length === 0 && (
                  <p className="text-sm text-gray-400 mt-2">
                    No knowledge bases available. Upload some first.
                  </p>
                )}
              </div>

              <div>
                <Label htmlFor="budget">Monthly Budget Limit ($)</Label>
                <Input
                  id="budget"
                  type="number"
                  value={formData.budget_limit}
                  onChange={(e) => setFormData(prev => ({ ...prev, budget_limit: e.target.value }))}
                  placeholder="Optional budget cap"
                  className="bg-[#2a2a4e] border-gray-600 text-white"
                />
              </div>

              <div>
                <Label>Allowed Models</Label>
                <div className="mt-2">
                  <Select onValueChange={addModel}>
                    <SelectTrigger className="bg-[#2a2a4e] border-gray-600 text-white">
                      <SelectValue placeholder="Add model..." />
                    </SelectTrigger>
                    <SelectContent className="bg-[#2a2a4e] border-gray-600">
                      {models.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.model_allowlist.map((model) => (
                      <Badge
                        key={model}
                        variant="secondary"
                        className="bg-green-600 cursor-pointer"
                        onClick={() => removeModel(model)}
                      >
                        {model}
                        <X className="h-3 w-3 ml-1" />
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex space-x-3">
                <Button
                  onClick={handleCreateGroup}
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Group
                </Button>
                <Button
                  variant="outline"
                  onClick={resetForm}
                  className="bg-[#2a2a4e] border-gray-600 text-white hover:bg-[#3a3a6e]"
                >
                  Reset
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Group Detail Modal */}
        {selectedGroup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-[#1a1a2e] border border-gray-700 rounded-lg p-6 max-w-lg w-full mx-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">{selectedGroup.name}</h3>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedGroup(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-gray-400">Description:</span>
                  <p>{selectedGroup.description || "No description"}</p>
                </div>
                <div>
                  <span className="text-gray-400">Knowledge Bases:</span>
                  <p>{selectedGroup.knowledge_base_ids.length} connected</p>
                </div>
                <div>
                  <span className="text-gray-400">Budget Limit:</span>
                  <p>${selectedGroup.budget_limit || "No limit"}</p>
                </div>
                <div>
                  <span className="text-gray-400">Agents:</span>
                  <p>{selectedGroup.agent_count} agents in this group</p>
                </div>
                <div>
                  <span className="text-gray-400">Created:</span>
                  <p>{new Date(selectedGroup.created_at).toLocaleString()}</p>
                </div>
              </div>
              <div className="flex space-x-2 mt-6">
                <Button
                  size="sm"
                  variant="outline"
                  className="bg-[#2a2a4e] border-gray-600 text-white hover:bg-[#3a3a6e]"
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleDeleteGroup(selectedGroup.id)}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}