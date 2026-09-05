"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { agentsApi } from "@/lib/api";
import { LANGUAGES, VOICE_PERSONAS, type Language, type VoicePersona } from "@/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const agentSchema = z.object({
  name: z
    .string()
    .min(3, "Name must be at least 3 characters")
    .max(64, "Name must be 64 characters or fewer"),
  persona_name: z.string().optional().or(z.literal("")),
  voice_persona: z.enum(VOICE_PERSONAS),
  language: z.enum(LANGUAGES),
  agent_prompt: z.string().min(10, "Agent prompt must be at least 10 characters"),
  introduction: z.string().min(10, "Introduction must be at least 10 characters"),
  objective: z.string().optional().or(z.literal("")),
  result_prompt: z.string().optional().or(z.literal("")),
});

type AgentFormValues = z.infer<typeof agentSchema>;

export default function NewAgentPage() {
  const router = useRouter();

  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentSchema),
    defaultValues: {
      name: "",
      persona_name: "",
      voice_persona: "NEHA" as VoicePersona,
      language: "ENGLISH" as Language,
      agent_prompt: "",
      introduction: "",
      objective: "",
      result_prompt: "",
    },
  });

  const { isSubmitting } = form.formState;

  const onSubmit = async (values: AgentFormValues) => {
    try {
      const payload = {
        ...values,
        persona_name: values.persona_name || null,
        objective: values.objective || "",
        result_prompt: values.result_prompt || "",
        result_schema: {
          interested: "Yes | No | Maybe",
          qualified: "Yes | No | Needs Review",
          salary_expectation: "number (in Lakhs per annum)",
          notice_period_weeks: "number",
          notes: "string",
        },
      };
      const created = await agentsApi.create(payload);
      toast.success(`Agent "${created.name}" created`);
      router.push("/agents");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create agent");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Voice Agent</h1>
        <p className="text-muted-foreground">
          Configure an AI agent for hiring calls
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Identity</CardTitle>
              <CardDescription>How the agent identifies itself</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Agent name *</FormLabel>
                      <FormControl>
                        <Input placeholder="Senior Recruiter Agent" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="persona_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Persona name</FormLabel>
                      <FormControl>
                        <Input placeholder="Priya" {...field} />
                      </FormControl>
                      <FormDescription>
                        The name the agent will use when introducing itself.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="voice_persona"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Voice persona</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {VOICE_PERSONAS.map((p) => (
                            <SelectItem key={p} value={p}>
                              {p}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="language"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Language</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {LANGUAGES.map((l) => (
                            <SelectItem key={l} value={l}>
                              {l}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Prompts</CardTitle>
              <CardDescription>
                Tell the agent how to behave on the call
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="agent_prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Agent prompt (system instructions) *</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={5}
                        placeholder="You are a professional HR recruiter calling candidates named {callee_name}..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="introduction"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Introduction script *</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={3}
                        placeholder="Hi {callee_name}! This is {persona_name} calling from {company}..."
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Placeholders: {"{callee_name}"}, {"{persona_name}"},{" "}
                      {"{company}"}, {"{job_title}"}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="objective"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Objective</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={2}
                        placeholder="Screen candidates for the {job_title} role at {company}..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="result_prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Result prompt</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={3}
                        placeholder="From this conversation, extract: interest, qualification, salary, notice period, notes..."
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Instructions for the AI to extract structured results.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push("/agents")}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create agent"}
            </Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
