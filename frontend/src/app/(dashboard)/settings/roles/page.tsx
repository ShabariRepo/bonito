"use client";

import { useState, useEffect } from "react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { 
  Shield, 
  Plus, 
  Trash2, 
  Edit,
  Users,
  Settings,
  Crown,
  UserCheck
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

interface Role {
  id: string;
  name: string;
  description: string | null;
  is_managed: boolean;
  permissions: Array<{
    action: string;
    resource_type: string;
    resource_ids: string[];
  }>;
  created_at: string;
}

interface RoleAssignment {
  id: string;
  user_id: string;
  role_id: string;
  scope_type: string;
  scope_id: string | null;
  user_name: string;
  role_name: string;
  scope_name: string | null;
  created_at: string;
}

interface User {
  id: string;
  name: string;
  email: string;
}

export default function RoleManagementPage() {
  const { toast } = useToast();
  const [roles, setRoles] = useState<Role[]>([]);
  const [assignments, setAssignments] = useState<RoleAssignment[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState("roles");

  // Create role form state
  const [createRoleForm, setCreateRoleForm] = useState({
    name: "",
    description: "",
    permissions: [] as Array<{ action: string; resource_type: string; resource_ids: string[] }>
  });

  // Create assignment form state  
  const [createAssignmentForm, setCreateAssignmentForm] = useState({
    user_id: "",
    role_id: "",
    scope_type: "org" as "org" | "project" | "group",
    scope_id: ""
  });

  useEffect(() => {
    fetchRoles();
    fetchAssignments();
    fetchUsers();
  }, []);

  const fetchRoles = async () => {
    try {
      const res = await apiRequest("/api/roles");
      if (res.ok) {
        const data = await res.json();
        setRoles(data);
      }
    } catch (error) {
      console.error("Failed to fetch roles:", error);
      toast({
        title: "Error",
        description: "Failed to load roles",
        variant: "destructive",
      });
    }
  };

  const fetchAssignments = async () => {
    try {
      const res = await apiRequest("/api/role-assignments");
      if (res.ok) {
        const data = await res.json();
        setAssignments(data);
      }
    } catch (error) {
      console.error("Failed to fetch assignments:", error);
    }
  };

  const fetchUsers = async () => {
    try {
      const res = await apiRequest("/api/users");
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch (error) {
      console.error("Failed to fetch users:", error);
    }
  };

  const handleCreateRole = async () => {
    if (!createRoleForm.name.trim()) {
      toast({
        title: "Error", 
        description: "Role name is required",
        variant: "destructive",
      });
      return;
    }

    try {
      const res = await apiRequest("/api/roles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createRoleForm),
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Role created successfully",
        });
        setCreateRoleForm({ name: "", description: "", permissions: [] });
        fetchRoles();
      } else {
        const errorData = await res.json();
        toast({
          title: "Error",
          description: errorData.detail || "Failed to create role",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to create role:", error);
      toast({
        title: "Error", 
        description: "Failed to create role",
        variant: "destructive",
      });
    }
  };

  const handleDeleteRole = async (roleId: string, roleName: string) => {
    if (!confirm(`Are you sure you want to delete the role "${roleName}"?`)) {
      return;
    }

    try {
      const res = await apiRequest(`/api/roles/${roleId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Role deleted successfully",
        });
        fetchRoles();
      } else {
        const errorData = await res.json();
        toast({
          title: "Error",
          description: errorData.detail || "Failed to delete role",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to delete role:", error);
      toast({
        title: "Error",
        description: "Failed to delete role", 
        variant: "destructive",
      });
    }
  };

  const handleCreateAssignment = async () => {
    if (!createAssignmentForm.user_id || !createAssignmentForm.role_id) {
      toast({
        title: "Error",
        description: "User and role are required",
        variant: "destructive",
      });
      return;
    }

    try {
      const payload = {
        ...createAssignmentForm,
        scope_id: createAssignmentForm.scope_id || null
      };

      const res = await apiRequest("/api/role-assignments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Role assigned successfully",
        });
        setCreateAssignmentForm({
          user_id: "",
          role_id: "",
          scope_type: "org",
          scope_id: ""
        });
        fetchAssignments();
      } else {
        const errorData = await res.json();
        toast({
          title: "Error",
          description: errorData.detail || "Failed to assign role",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to assign role:", error);
      toast({
        title: "Error",
        description: "Failed to assign role",
        variant: "destructive",
      });
    }
  };

  const handleDeleteAssignment = async (assignmentId: string) => {
    if (!confirm("Are you sure you want to remove this role assignment?")) {
      return;
    }

    try {
      const res = await apiRequest(`/api/role-assignments/${assignmentId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        toast({
          title: "Success",
          description: "Role assignment removed successfully",
        });
        fetchAssignments();
      } else {
        toast({
          title: "Error",
          description: "Failed to remove role assignment",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Failed to remove assignment:", error);
      toast({
        title: "Error",
        description: "Failed to remove role assignment",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Role Management</h1>
          <p className="text-gray-400">
            Manage roles and permissions for your organization
          </p>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="grid w-full grid-cols-3 bg-[#2a2a4e]">
          <TabsTrigger value="roles" className="data-[state=active]:bg-blue-600">
            <Shield className="h-4 w-4 mr-2" />
            Roles
          </TabsTrigger>
          <TabsTrigger value="assignments" className="data-[state=active]:bg-blue-600">
            <UserCheck className="h-4 w-4 mr-2" />
            Assignments
          </TabsTrigger>
          <TabsTrigger value="create" className="data-[state=active]:bg-blue-600">
            <Plus className="h-4 w-4 mr-2" />
            Create
          </TabsTrigger>
        </TabsList>

        <TabsContent value="roles" className="space-y-4">
          <div className="grid gap-4">
            {roles.map((role) => (
              <Card key={role.id} className="bg-[#2a2a4e] border-gray-700">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <CardTitle className="flex items-center">
                        {role.is_managed && (
                          <Crown className="h-4 w-4 mr-2 text-yellow-500" />
                        )}
                        {role.name}
                      </CardTitle>
                      <Badge 
                        variant={role.is_managed ? "default" : "secondary"}
                        className={role.is_managed ? "bg-yellow-600" : "bg-green-600"}
                      >
                        {role.is_managed ? "Managed" : "Custom"}
                      </Badge>
                    </div>
                    {!role.is_managed && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteRole(role.id, role.name)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                  {role.description && (
                    <p className="text-sm text-gray-400">{role.description}</p>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Label className="text-sm text-gray-300">Permissions:</Label>
                    <div className="flex flex-wrap gap-2">
                      {role.permissions.map((perm, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {perm.action} on {perm.resource_type}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="assignments" className="space-y-4">
          <Card className="bg-[#2a2a4e] border-gray-700">
            <CardHeader>
              <CardTitle>Role Assignments</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Scope</TableHead>
                    <TableHead>Assigned</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assignments.map((assignment) => (
                    <TableRow key={assignment.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{assignment.user_name}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{assignment.role_name}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <div>{assignment.scope_type}</div>
                          {assignment.scope_name && (
                            <div className="text-gray-400">{assignment.scope_name}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-gray-400">
                        {new Date(assignment.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteAssignment(assignment.id)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="create" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Create Role */}
            <Card className="bg-[#2a2a4e] border-gray-700">
              <CardHeader>
                <CardTitle>Create Custom Role</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="role-name">Role Name</Label>
                  <Input
                    id="role-name"
                    value={createRoleForm.name}
                    onChange={(e) => setCreateRoleForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Marketing Manager"
                    className="bg-[#1a1a2e] border-gray-600 text-white"
                  />
                </div>
                <div>
                  <Label htmlFor="role-description">Description</Label>
                  <Textarea
                    id="role-description"
                    value={createRoleForm.description}
                    onChange={(e) => setCreateRoleForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Brief description of this role"
                    className="bg-[#1a1a2e] border-gray-600 text-white"
                  />
                </div>
                <Button onClick={handleCreateRole} className="w-full bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Role
                </Button>
              </CardContent>
            </Card>

            {/* Assign Role */}
            <Card className="bg-[#2a2a4e] border-gray-700">
              <CardHeader>
                <CardTitle>Assign Role</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>User</Label>
                  <Select value={createAssignmentForm.user_id} onValueChange={(value) => 
                    setCreateAssignmentForm(prev => ({ ...prev, user_id: value }))
                  }>
                    <SelectTrigger className="bg-[#1a1a2e] border-gray-600 text-white">
                      <SelectValue placeholder="Select user..." />
                    </SelectTrigger>
                    <SelectContent className="bg-[#2a2a4e] border-gray-600">
                      {users.map((user) => (
                        <SelectItem key={user.id} value={user.id}>
                          {user.name} ({user.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Role</Label>
                  <Select value={createAssignmentForm.role_id} onValueChange={(value) => 
                    setCreateAssignmentForm(prev => ({ ...prev, role_id: value }))
                  }>
                    <SelectTrigger className="bg-[#1a1a2e] border-gray-600 text-white">
                      <SelectValue placeholder="Select role..." />
                    </SelectTrigger>
                    <SelectContent className="bg-[#2a2a4e] border-gray-600">
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Scope</Label>
                  <Select value={createAssignmentForm.scope_type} onValueChange={(value: any) => 
                    setCreateAssignmentForm(prev => ({ ...prev, scope_type: value }))
                  }>
                    <SelectTrigger className="bg-[#1a1a2e] border-gray-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#2a2a4e] border-gray-600">
                      <SelectItem value="org">Organization</SelectItem>
                      <SelectItem value="project">Project</SelectItem>
                      <SelectItem value="group">Group</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleCreateAssignment} className="w-full bg-green-600 hover:bg-green-700">
                  <UserCheck className="h-4 w-4 mr-2" />
                  Assign Role
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}