"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";

type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  estimated_deploy_time: string;
  features: string[];
};

export default function TemplatesPage() {
  const { get, post } = useApi();
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await get<Template[]>("/api/templates");
        setTemplates(data);
      } catch {
        // API may not be connected
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  async function deploy(templateId: string) {
    setDeploying(templateId);
    try {
      const result = await post<{ deployment_id: string }>(
        "/api/templates/deploy",
        { template_id: templateId }
      );
      router.push(`/dashboard/deployments/${result.deployment_id}`);
    } catch {
      setDeploying(null);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-forest-dark">Templates</h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          Pre-built AI models ready to deploy in one click.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-48 animate-pulse rounded-xl bg-white border border-mist"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="flex flex-col rounded-xl border border-mist bg-white p-5 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">{t.icon}</span>
                <div>
                  <h3 className="text-sm font-semibold text-forest-dark">
                    {t.name}
                  </h3>
                  <span className="text-xs text-forest-dark/40 capitalize">
                    {t.category}
                  </span>
                </div>
              </div>
              <p className="text-xs text-forest-dark/60 leading-relaxed flex-1">
                {t.description}
              </p>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-forest-dark/40">
                  ~{t.estimated_deploy_time}
                </span>
                <button
                  onClick={() => deploy(t.id)}
                  disabled={deploying === t.id}
                  className="rounded-lg bg-forest px-3 py-1.5 text-xs font-medium text-white hover:bg-forest-hover transition-colors disabled:opacity-50"
                >
                  {deploying === t.id ? "Deploying..." : "Deploy"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
