"use client";

import { useState } from "react";

import { createScenario, updateScenario, ScenarioInput } from "@/services/api/admin/scenarios";

export function ScenarioForm({
  scenarioId,
  initialValues,
  version,
  onSaved,
}: {
  scenarioId?: string;
  initialValues?: Partial<ScenarioInput>;
  version?: string | null;
  onSaved?: (newVersion?: string | null) => void;
}) {
  const [values, setValues] = useState<ScenarioInput>({
      metadata: {
      domain: initialValues?.metadata?.domain ?? "",
      title: initialValues?.metadata?.title ?? "",
      slug: initialValues?.metadata?.slug ?? "",
      scenarioType: initialValues?.metadata?.scenarioType ?? "practice",
      difficulty: initialValues?.metadata?.difficulty ?? "medium",
      conflictLevel: initialValues?.metadata?.conflictLevel ?? "medium",
      estimatedDurationMinutes: initialValues?.metadata?.estimatedDurationMinutes ?? 5,
      tags: initialValues?.metadata?.tags ?? [],
    },
    context: {
      situation: initialValues?.context?.situation ?? "",
      background: initialValues?.context?.background ?? "",
      setting: initialValues?.context?.setting ?? "",
    },
    simulationConfig: {
      ai: initialValues?.simulationConfig?.ai ?? { name: "", role: "", personality: [], motivations: [], constraints: [], tendencies: [], knowledge: [], emotionalState: "" },
      trainee: initialValues?.simulationConfig?.trainee ?? { name: "", role: "", personality: [], motivations: [], constraints: [], tendencies: [], knowledge: [], emotionalState: "" },
      language: initialValues?.simulationConfig?.language ?? "en",
      conversationStart: initialValues?.simulationConfig?.conversationStart ?? {
        speakerRoleId: "ai",
        initialPromptToUser: "",
      },
      conversationRules: initialValues?.simulationConfig?.conversationRules ?? {
        stayInCharacter: true,
        allowNarration: false,
        coachingAllowed: false,
        tone: "professional",
      },
      conversationDynamics: initialValues?.simulationConfig?.conversationDynamics ?? {
        typicalBehaviors: [],
        possibleResponses: [],
      },
      decisionConstraints: initialValues?.simulationConfig?.decisionConstraints ?? {
        alternativeOptions: [],
      },
      conversationEndConditions: initialValues?.simulationConfig?.conversationEndConditions ?? {
        possibleEndStates: [],
      },
    },
    evaluationConfig: {
      learningObjectives: initialValues?.evaluationConfig?.learningObjectives ?? [],
      evaluationCriteria: initialValues?.evaluationConfig?.evaluationCriteria ?? [],
      skillsAssessed: initialValues?.evaluationConfig?.skillsAssessed ?? [],
      scoring: initialValues?.evaluationConfig?.scoring ?? { scale: "1-5", criteriaWeighting: {} },
      evaluationInstructionsForLLM: initialValues?.evaluationConfig?.evaluationInstructionsForLLM ?? "",
    },
    status: initialValues?.status ?? "draft",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleMetadataChange = (field: keyof ScenarioInput["metadata"]) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      let value: string | number = e.target.value;
      if (field === "estimatedDurationMinutes") value = Number(value);
      setValues((prev) => ({ ...prev, metadata: { ...prev.metadata, [field]: value } }));
    };

  const handleContextChange = (field: keyof ScenarioInput["context"]) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((prev) => ({ ...prev, context: { ...prev.context, [field]: e.target.value } }));
    };

  const handleAiChange = (field: keyof ScenarioInput["simulationConfig"]["ai"]) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, ai: { ...prev.simulationConfig.ai, [field]: e.target.value } } }));
    };

  const handleAiArrayChange = (field: keyof ScenarioInput["simulationConfig"]["ai"]) =>
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
      setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, ai: { ...prev.simulationConfig.ai, [field]: items } } }));
    };

  const handleTraineeChange = (field: keyof ScenarioInput["simulationConfig"]["trainee"]) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, trainee: { ...prev.simulationConfig.trainee, [field]: e.target.value } } }));
    };

  const handleTraineeArrayChange = (field: keyof ScenarioInput["simulationConfig"]["trainee"]) =>
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
      setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, trainee: { ...prev.simulationConfig.trainee, [field]: items } } }));
    };

  const handleStringArrayChange = (
    section: "metadata" | "evaluationConfig",
    field: string
  ) => (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
    setValues((prev) => ({
      ...prev,
      [section]: { ...prev[section as keyof ScenarioInput] as any, [field]: items },
    }));
  };

  const handleRulesCheckboxChange = (field: keyof ScenarioInput["simulationConfig"]["conversationRules"]) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setValues((prev) => ({
        ...prev,
        simulationConfig: {
          ...prev.simulationConfig,
          conversationRules: { ...prev.simulationConfig.conversationRules, [field]: e.target.checked },
        },
      }));
    };

  const handleRulesTextChange = (field: keyof ScenarioInput["simulationConfig"]["conversationRules"]) =>
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setValues((prev) => ({
        ...prev,
        simulationConfig: {
          ...prev.simulationConfig,
          conversationRules: { ...prev.simulationConfig.conversationRules, [field]: e.target.value },
        },
      }));
    };

  const handleDynamicsArrayChange = (field: keyof ScenarioInput["simulationConfig"]["conversationDynamics"]) =>
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
      setValues((prev) => ({
        ...prev,
        simulationConfig: {
          ...prev.simulationConfig,
          conversationDynamics: { ...prev.simulationConfig.conversationDynamics, [field]: items },
        },
      }));
    };

  const handleDecisionConstraintsOptionsChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
    setValues((prev) => ({
      ...prev,
      simulationConfig: {
        ...prev.simulationConfig,
        decisionConstraints: { ...prev.simulationConfig.decisionConstraints, alternativeOptions: items },
      },
    }));
  };

  const handleDecisionConstraintsMaxRaiseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value ? Number(e.target.value) : undefined;
    setValues((prev) => ({
      ...prev,
      simulationConfig: {
        ...prev.simulationConfig,
        decisionConstraints: { ...prev.simulationConfig.decisionConstraints, maxRaiseWithoutHigherApprovalPercent: val },
      },
    }));
  };

  const handleEndStatesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const items = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean);
    setValues((prev) => ({
      ...prev,
      simulationConfig: {
        ...prev.simulationConfig,
        conversationEndConditions: { possibleEndStates: items },
      },
    }));
  };

  const handleEvaluationCriteriaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const lines = e.target.value.split("\n").filter(Boolean);
    const criteria = lines.map((line) => {
      const parts = line.split("|");
      const id = parts[0]?.trim() || "";
      const description = parts.slice(1).join("|").trim();
      return { id, description };
    });
    setValues((prev) => ({
      ...prev,
      evaluationConfig: { ...prev.evaluationConfig, evaluationCriteria: criteria },
    }));
  };

  const handleCriteriaWeightingChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const lines = e.target.value.split("\n").filter(Boolean);
    const weighting: Record<string, number> = {};
    lines.forEach((line) => {
      const parts = line.split("|");
      const id = parts[0]?.trim();
      const weight = Number(parts[1]?.trim());
      if (id && !isNaN(weight)) {
        weighting[id] = weight;
      }
    });
    setValues((prev) => ({
      ...prev,
      evaluationConfig: {
        ...prev.evaluationConfig,
        scoring: { ...prev.evaluationConfig.scoring, criteriaWeighting: weighting },
      },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (scenarioId) {
        const result = await updateScenario(scenarioId, values, version ?? "");
        setNotice("Saved");
        onSaved?.(result.version);
      } else {
        await createScenario(values);
        setNotice("Created");
      }
      onSaved?.();
    } catch (err: any) {
      if (err?.message === "stale") setError("This scenario was updated elsewhere. Refresh and retry.");
      else setError(err?.message ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: 12, maxWidth: 800 }}>
      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>Metadata</strong>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Title</span>
          <input required value={values.metadata.title} onChange={handleMetadataChange("title")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Slug</span>
          <input value={values.metadata.slug || ""} onChange={handleMetadataChange("slug")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Domain (Category)</span>
          <input required value={values.metadata.domain} onChange={handleMetadataChange("domain")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Scenario Type</span>
          <input required value={values.metadata.scenarioType} onChange={handleMetadataChange("scenarioType")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Difficulty</span>
            <select value={values.metadata.difficulty} onChange={handleMetadataChange("difficulty")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", background: "#fff" }}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Conflict Level</span>
            <select value={values.metadata.conflictLevel} onChange={handleMetadataChange("conflictLevel")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", background: "#fff" }}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Duration (min)</span>
            <input type="number" required value={values.metadata.estimatedDurationMinutes} onChange={handleMetadataChange("estimatedDurationMinutes")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          </label>
        </div>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Tags (one per line)</span>
          <textarea value={values.metadata.tags.join("\n")} onChange={handleStringArrayChange("metadata", "tags")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
      </div>

      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>Context</strong>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Situation</span>
          <textarea required value={values.context.situation} onChange={handleContextChange("situation")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Background</span>
          <textarea value={values.context.background} onChange={handleContextChange("background")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Setting</span>
          <input value={values.context.setting} onChange={handleContextChange("setting")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </label>
      </div>

      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>Simulation Config</strong>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Language</span>
          <select value={values.simulationConfig.language} onChange={(e) => setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, language: e.target.value } }))} style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", background: "#fff" }}>
            <option value="en">English</option>
            <option value="zh">Chinese</option>
          </select>
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Who Talks First</span>
          <select
            value={values.simulationConfig.conversationStart.speakerRoleId}
            onChange={(e) => setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, conversationStart: { ...prev.simulationConfig.conversationStart, speakerRoleId: e.target.value as "ai" | "trainee" } } }))}
            style={{ padding: 10, borderRadius: 8, border: "1px solid #d9d3cb", background: "#fff" }}
          >
            <option value="ai">AI</option>
            <option value="trainee">Trainee</option>
          </select>
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span>Initial Prompt To User</span>
          <textarea value={values.simulationConfig.conversationStart.initialPromptToUser} onChange={(e) => setValues((prev) => ({ ...prev, simulationConfig: { ...prev.simulationConfig, conversationStart: { ...prev.simulationConfig.conversationStart, initialPromptToUser: e.target.value } } }))} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>

        <div style={{ display: "grid", gap: 6, paddingLeft: 12, borderLeft: "2px solid #e4ddd4" }}>
          <em>AI Persona</em>
          <input placeholder="Name" value={values.simulationConfig.ai.name} onChange={handleAiChange("name")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          <input placeholder="Role" value={values.simulationConfig.ai.role} onChange={handleAiChange("role")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          <textarea placeholder="Personality (one per line)" value={values.simulationConfig.ai.personality.join("\n")} onChange={handleAiArrayChange("personality")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Motivations (one per line)" value={values.simulationConfig.ai.motivations.join("\n")} onChange={handleAiArrayChange("motivations")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Constraints (one per line)" value={values.simulationConfig.ai.constraints.join("\n")} onChange={handleAiArrayChange("constraints")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Tendencies (one per line)" value={values.simulationConfig.ai.tendencies.join("\n")} onChange={handleAiArrayChange("tendencies")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Knowledge (one per line)" value={values.simulationConfig.ai.knowledge.join("\n")} onChange={handleAiArrayChange("knowledge")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <input placeholder="Emotional State" value={values.simulationConfig.ai.emotionalState} onChange={handleAiChange("emotionalState")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </div>

        <div style={{ display: "grid", gap: 6, paddingLeft: 12, borderLeft: "2px solid #e4ddd4" }}>
          <em>Trainee Persona</em>
          <input placeholder="Name" value={values.simulationConfig.trainee.name} onChange={handleTraineeChange("name")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          <input placeholder="Role" value={values.simulationConfig.trainee.role} onChange={handleTraineeChange("role")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          <textarea placeholder="Personality (one per line)" value={values.simulationConfig.trainee.personality.join("\n")} onChange={handleTraineeArrayChange("personality")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Motivations (one per line)" value={values.simulationConfig.trainee.motivations.join("\n")} onChange={handleTraineeArrayChange("motivations")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Constraints (one per line)" value={values.simulationConfig.trainee.constraints.join("\n")} onChange={handleTraineeArrayChange("constraints")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Tendencies (one per line)" value={values.simulationConfig.trainee.tendencies.join("\n")} onChange={handleTraineeArrayChange("tendencies")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Knowledge (one per line)" value={values.simulationConfig.trainee.knowledge.join("\n")} onChange={handleTraineeArrayChange("knowledge")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <input placeholder="Emotional State" value={values.simulationConfig.trainee.emotionalState} onChange={handleTraineeChange("emotionalState")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </div>

        <div style={{ display: "grid", gap: 6, paddingLeft: 12, borderLeft: "2px solid #e4ddd4" }}>
          <em>Conversation Rules</em>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}><input type="checkbox" checked={values.simulationConfig.conversationRules.stayInCharacter} onChange={handleRulesCheckboxChange("stayInCharacter")} /> Stay in Character</label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}><input type="checkbox" checked={values.simulationConfig.conversationRules.allowNarration} onChange={handleRulesCheckboxChange("allowNarration")} /> Allow Narration</label>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}><input type="checkbox" checked={values.simulationConfig.conversationRules.coachingAllowed} onChange={handleRulesCheckboxChange("coachingAllowed")} /> Coaching Allowed</label>
          <input placeholder="Tone (e.g. professional, confrontational)" value={values.simulationConfig.conversationRules.tone} onChange={handleRulesTextChange("tone")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
        </div>

        <div style={{ display: "grid", gap: 6, paddingLeft: 12, borderLeft: "2px solid #e4ddd4" }}>
          <em>Conversation Dynamics</em>
          <textarea placeholder="Typical Behaviors (one per line)" value={values.simulationConfig.conversationDynamics.typicalBehaviors.join("\n")} onChange={handleDynamicsArrayChange("typicalBehaviors")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
          <textarea placeholder="Possible Responses (one per line)" value={values.simulationConfig.conversationDynamics.possibleResponses.join("\n")} onChange={handleDynamicsArrayChange("possibleResponses")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
        </div>

        <div style={{ display: "grid", gap: 6, paddingLeft: 12, borderLeft: "2px solid #e4ddd4" }}>
          <em>Decision Constraints</em>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Max Raise % without higher approval (Optional)</span>
            <input type="number" placeholder="10" value={values.simulationConfig.decisionConstraints.maxRaiseWithoutHigherApprovalPercent ?? ""} onChange={handleDecisionConstraintsMaxRaiseChange} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          </label>
          <textarea placeholder="Alternative Options (one per line)" value={values.simulationConfig.decisionConstraints.alternativeOptions.join("\n")} onChange={handleDecisionConstraintsOptionsChange} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 40 }} />
        </div>

        <label style={{ display: "grid", gap: 6 }}>
          <span>End Conditions (one per line)</span>
          <textarea value={values.simulationConfig.conversationEndConditions.possibleEndStates.join("\n")} onChange={handleEndStatesChange} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
      </div>

      <div style={{ display: "grid", gap: 8, border: "1px solid #e4ddd4", borderRadius: 10, padding: 12 }}>
        <strong>Evaluation Config</strong>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Learning Objectives (one per line)</span>
          <textarea value={values.evaluationConfig.learningObjectives.join("\n")} onChange={handleStringArrayChange("evaluationConfig", "learningObjectives")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
        
        <label style={{ display: "grid", gap: 6 }}>
          <span>Skills Assessed (one Label per line)</span>
          <textarea value={values.evaluationConfig.skillsAssessed.join("\n")} onChange={handleStringArrayChange("evaluationConfig", "skillsAssessed")} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>

        <label style={{ display: "grid", gap: 6 }}>
          <span>Evaluation Criteria (Format: id|description per line)</span>
          <textarea
            placeholder="e.g. tone|User kept a professional tone"
            value={values.evaluationConfig.evaluationCriteria.map((c) => `${c.id}|${c.description}`).join("\n")}
            onChange={handleEvaluationCriteriaChange}
            style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }}
          />
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 8 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Scoring Scale</span>
            <input value={values.evaluationConfig.scoring.scale} onChange={(e) => setValues((prev) => ({ ...prev, evaluationConfig: { ...prev.evaluationConfig, scoring: { ...prev.evaluationConfig.scoring, scale: e.target.value } } }))} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb" }} />
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Criteria Weighting (Format: id|weight per line)</span>
            <textarea
              placeholder="e.g. tone|2"
              value={Object.entries(values.evaluationConfig.scoring.criteriaWeighting).map(([id, weight]) => `${id}|${weight}`).join("\n")}
              onChange={handleCriteriaWeightingChange}
              style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }}
            />
          </label>
        </div>

        <label style={{ display: "grid", gap: 6 }}>
          <span>Evaluation Instructions For LLM</span>
          <textarea value={values.evaluationConfig.evaluationInstructionsForLLM} onChange={(e) => setValues((prev) => ({ ...prev, evaluationConfig: { ...prev.evaluationConfig, evaluationInstructionsForLLM: e.target.value } }))} style={{ padding: 8, borderRadius: 8, border: "1px solid #d9d3cb", minHeight: 60 }} />
        </label>
      </div>

      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {notice ? <p style={{ color: "#1f7a3d" }}>{notice}</p> : null}

      <button
        type="submit"
        disabled={saving}
        style={{
          padding: "10px 16px",
          borderRadius: 10,
          border: "none",
          background: "#2f2a24",
          color: "#f7f3ec",
          cursor: "pointer",
          fontWeight: 700,
        }}
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </form>
  );
}
