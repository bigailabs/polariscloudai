"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useApi } from "@/lib/hooks";
import { useToast } from "@/components/toast";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

type TemplateParameter = {
  name: string;
  label: string;
  type: string;
  required: boolean;
  default?: string | number;
  placeholder?: string;
  options?: { value: string; label: string }[];
  description?: string;
};

type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  default_port: number;
  estimated_deploy_time: string;
  access_type: string;
  features: string[];
  parameters: TemplateParameter[];
};

type SortOption = "popular" | "newest" | "name";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const CATEGORIES: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "ai_ml", label: "AI & ML" },
  { key: "development", label: "Development" },
  { key: "desktop", label: "Desktop" },
  { key: "games", label: "Games" },
];

const CATEGORY_LABELS: Record<string, string> = {
  ai_ml: "AI & Machine Learning",
  development: "Development Tools",
  desktop: "Cloud Desktops",
  games: "Gaming Servers",
  infrastructure: "Infrastructure",
};

const FEATURED_IDS = new Set(["ollama", "jupyter"]);

/** Static popularity ranking used when sort = "popular" */
const POPULARITY: Record<string, number> = {
  ollama: 100,
  jupyter: 90,
  "ubuntu-desktop": 80,
  "transformer-labs": 70,
  "dev-terminal": 60,
  minecraft: 50,
  valheim: 40,
  terraria: 30,
  factorio: 20,
};

const ACCESS_LABELS: Record<string, string> = {
  web: "Web UI",
  terminal: "Terminal",
  game: "Game Client",
  api: "API",
  vnc: "VNC",
};

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function TemplatesPage() {
  const { get, post } = useApi();
  const router = useRouter();
  const toast = useToast();

  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [sort, setSort] = useState<SortOption>("popular");

  // Detail panel
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null
  );

  useEffect(() => {
    async function load() {
      try {
        const data = await get<{ templates: Template[] }>("/api/templates");
        setTemplates(data.templates ?? []);
      } catch {
        // API may not be connected
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [get]);

  /* ---- derived data ---- */

  const filtered = useMemo(() => {
    let list = templates;

    // Category filter
    if (activeCategory !== "all") {
      list = list.filter((t) => t.category === activeCategory);
    }

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.features.some((f) => f.toLowerCase().includes(q))
      );
    }

    // Sort
    list = [...list].sort((a, b) => {
      if (sort === "popular")
        return (POPULARITY[b.id] ?? 0) - (POPULARITY[a.id] ?? 0);
      if (sort === "name") return a.name.localeCompare(b.name);
      // "newest" -- keep original registry order
      return 0;
    });

    return list;
  }, [templates, activeCategory, search, sort]);

  /** Templates grouped by category (preserves sort within each group) */
  const grouped = useMemo(() => {
    const map = new Map<string, Template[]>();
    for (const t of filtered) {
      if (!map.has(t.category)) map.set(t.category, []);
      map.get(t.category)!.push(t);
    }
    return map;
  }, [filtered]);

  /* ---- handlers ---- */

  async function deploy(templateId: string) {
    setDeploying(templateId);
    try {
      const result = await post<{ deployment_id: string }>(
        "/api/templates/deploy",
        { template_id: templateId }
      );
      toast.success("Deployment started! Redirecting...");
      router.push(`/dashboard/deployments/${result.deployment_id}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start deployment";
      toast.error(message);
      setDeploying(null);
    }
  }

  const openDetail = useCallback((t: Template) => setSelectedTemplate(t), []);
  const closeDetail = useCallback(() => setSelectedTemplate(null), []);

  /* ---- render ---- */

  return (
    <div className="relative">
      {/* ===== Header ===== */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-forest-dark">
          Template Marketplace
        </h1>
        <p className="mt-1 text-sm text-forest-dark/60">
          One-click deployable infrastructure, AI models, dev tools, and game
          servers.
        </p>
      </div>

      {/* ===== Search ===== */}
      <div className="relative mb-5">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
          <SearchIcon />
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search templates by name, description, or feature..."
          className="w-full rounded-xl border border-mist bg-white py-3 pl-11 pr-4 text-sm text-forest-dark placeholder:text-forest-dark/30 outline-none focus:border-forest/40 focus:ring-2 focus:ring-forest/10 transition-all"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute inset-y-0 right-0 flex items-center pr-4 text-forest-dark/30 hover:text-forest-dark/60 transition-colors"
          >
            <XIcon />
          </button>
        )}
      </div>

      {/* ===== Filters row ===== */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* Category chips */}
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              onClick={() => setActiveCategory(c.key)}
              className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-all ${
                activeCategory === c.key
                  ? "bg-forest text-white shadow-sm"
                  : "bg-white text-forest-dark/60 border border-mist hover:border-forest/30 hover:text-forest-dark"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Sort */}
        <div className="flex items-center gap-2 text-xs text-forest-dark/50">
          <span>Sort:</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOption)}
            className="rounded-lg border border-mist bg-white px-2.5 py-1.5 text-xs text-forest-dark outline-none focus:border-forest/40 transition-colors cursor-pointer"
          >
            <option value="popular">Popular</option>
            <option value="newest">Newest</option>
            <option value="name">Name A-Z</option>
          </select>
        </div>
      </div>

      {/* ===== Content ===== */}
      {loading ? (
        <LoadingSkeleton />
      ) : filtered.length === 0 ? (
        <EmptyState search={search} onClear={() => setSearch("")} />
      ) : activeCategory === "all" ? (
        /* Grouped view */
        <div className="space-y-10">
          {Array.from(grouped.entries()).map(([cat, items]) => (
            <section key={cat}>
              <h2 className="mb-4 text-base font-semibold text-forest-dark">
                {CATEGORY_LABELS[cat] ?? cat}
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((t) => (
                  <TemplateCard
                    key={t.id}
                    template={t}
                    deploying={deploying}
                    onDeploy={deploy}
                    onSelect={openDetail}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        /* Single-category flat grid */
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              deploying={deploying}
              onDeploy={deploy}
              onSelect={openDetail}
            />
          ))}
        </div>
      )}

      {/* ===== Detail panel ===== */}
      <DetailPanel
        template={selectedTemplate}
        deploying={deploying}
        onDeploy={deploy}
        onClose={closeDetail}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Template Card                                                     */
/* ------------------------------------------------------------------ */

function TemplateCard({
  template: t,
  deploying,
  onDeploy,
  onSelect,
}: {
  template: Template;
  deploying: string | null;
  onDeploy: (id: string) => void;
  onSelect: (t: Template) => void;
}) {
  const isFeatured = FEATURED_IDS.has(t.id);

  return (
    <div
      onClick={() => onSelect(t)}
      className="group relative flex flex-col rounded-xl border border-mist bg-white p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-forest/20 hover:-translate-y-0.5"
    >
      {/* Featured badge */}
      {isFeatured && (
        <span className="absolute -top-2.5 right-4 inline-flex items-center gap-1 rounded-full bg-copper/10 px-2.5 py-0.5 text-[10px] font-semibold text-copper">
          <StarIcon />
          Featured
        </span>
      )}

      {/* Icon + category */}
      <div className="flex items-start justify-between mb-3">
        <span className="text-3xl leading-none">{t.icon}</span>
        <CategoryPill category={t.category} />
      </div>

      {/* Name */}
      <h3 className="text-sm font-semibold text-forest-dark group-hover:text-forest transition-colors">
        {t.name}
      </h3>

      {/* Description (2-line clamp) */}
      <p className="mt-1 text-xs text-forest-dark/55 leading-relaxed line-clamp-2 flex-1">
        {t.description}
      </p>

      {/* Feature tags */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {deriveFeatureTags(t).map((tag) => (
          <span
            key={tag}
            className="rounded-md bg-sage px-2 py-0.5 text-[10px] font-medium text-forest-dark/50"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between border-t border-mist pt-3">
        <span className="text-[11px] text-forest-dark/40">
          ~{t.estimated_deploy_time}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDeploy(t.id);
          }}
          disabled={deploying === t.id}
          className="rounded-lg bg-forest px-3.5 py-1.5 text-xs font-medium text-white hover:bg-forest-hover transition-colors disabled:opacity-50"
        >
          {deploying === t.id ? "Deploying..." : "Deploy"}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Detail Slide-Over Panel                                           */
/* ------------------------------------------------------------------ */

function DetailPanel({
  template,
  deploying,
  onDeploy,
  onClose,
}: {
  template: Template | null;
  deploying: string | null;
  onDeploy: (id: string) => void;
  onClose: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (template) {
      document.addEventListener("keydown", handleKey);
      return () => document.removeEventListener("keydown", handleKey);
    }
  }, [template, onClose]);

  const open = template !== null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-forest-dark/20 backdrop-blur-sm transition-opacity duration-200 ${
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {template && (
          <div className="flex h-full flex-col overflow-y-auto">
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-mist bg-white px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{template.icon}</span>
                <div>
                  <h2 className="text-lg font-semibold text-forest-dark">
                    {template.name}
                  </h2>
                  <div className="flex items-center gap-2 mt-0.5">
                    <CategoryPill category={template.category} />
                    {FEATURED_IDS.has(template.id) && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-copper">
                        <StarIcon />
                        Featured
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-2 text-forest-dark/40 hover:bg-sage hover:text-forest-dark/70 transition-colors"
              >
                <XIcon />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 px-6 py-6 space-y-6">
              {/* Description */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-forest-dark/40 mb-2">
                  Description
                </h3>
                <p className="text-sm text-forest-dark/70 leading-relaxed">
                  {template.description}
                </p>
              </div>

              {/* Quick info */}
              <div className="grid grid-cols-3 gap-4">
                <InfoBlock
                  label="Deploy time"
                  value={`~${template.estimated_deploy_time}`}
                />
                <InfoBlock
                  label="Access type"
                  value={
                    ACCESS_LABELS[template.access_type] ?? template.access_type
                  }
                />
                <InfoBlock
                  label="Default port"
                  value={String(template.default_port)}
                />
              </div>

              {/* Features */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-forest-dark/40 mb-3">
                  Features
                </h3>
                <ul className="space-y-2">
                  {template.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-sm text-forest-dark/70"
                    >
                      <CheckIcon />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Parameters preview */}
              {template.parameters.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-forest-dark/40 mb-3">
                    Configuration parameters
                  </h3>
                  <div className="space-y-2">
                    {template.parameters.map((p) => (
                      <div
                        key={p.name}
                        className="flex items-center justify-between rounded-lg border border-mist bg-sage/50 px-3.5 py-2.5"
                      >
                        <div>
                          <span className="text-sm font-medium text-forest-dark">
                            {p.label}
                          </span>
                          {p.description && (
                            <p className="text-xs text-forest-dark/40 mt-0.5">
                              {p.description}
                            </p>
                          )}
                        </div>
                        <span className="text-xs text-forest-dark/40 font-mono">
                          {p.type === "select"
                            ? `${p.options?.length ?? 0} options`
                            : p.default !== undefined
                              ? String(p.default)
                              : p.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer CTA */}
            <div className="sticky bottom-0 border-t border-mist bg-white px-6 py-4">
              <button
                onClick={() => onDeploy(template.id)}
                disabled={deploying === template.id}
                className="w-full rounded-xl bg-forest py-3 text-sm font-semibold text-white hover:bg-forest-hover transition-colors disabled:opacity-50"
              >
                {deploying === template.id
                  ? "Deploying..."
                  : "Deploy this template"}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers & small components                                        */
/* ------------------------------------------------------------------ */

function CategoryPill({ category }: { category: string }) {
  const labels: Record<string, string> = {
    ai_ml: "AI & ML",
    development: "Dev",
    desktop: "Desktop",
    games: "Games",
    infrastructure: "Infra",
  };
  return (
    <span className="rounded-full bg-mist px-2 py-0.5 text-[10px] font-medium text-forest-dark/50">
      {labels[category] ?? category}
    </span>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-mist bg-sage/50 px-3 py-2.5 text-center">
      <p className="text-[10px] font-medium uppercase tracking-wider text-forest-dark/40 mb-0.5">
        {label}
      </p>
      <p className="text-sm font-medium text-forest-dark">{value}</p>
    </div>
  );
}

/** Derive compact feature tags from template data */
function deriveFeatureTags(t: Template): string[] {
  const tags: string[] = [];
  const allText = (t.features.join(" ") + " " + t.description).toLowerCase();

  if (allText.includes("gpu") || allText.includes("cuda")) tags.push("GPU");
  if (t.access_type === "web" || allText.includes("web ui"))
    tags.push("Web UI");
  if (
    t.access_type === "terminal" ||
    allText.includes("terminal") ||
    allText.includes("ssh")
  )
    tags.push("SSH");
  if (allText.includes("persistent")) tags.push("Persistent");
  if (allText.includes("api")) tags.push("API");
  if (t.access_type === "game") tags.push("Multiplayer");

  return tags.slice(0, 4);
}

function LoadingSkeleton() {
  return (
    <div className="space-y-10">
      {[1, 2].map((section) => (
        <div key={section}>
          <div className="mb-4 h-5 w-40 animate-pulse rounded bg-mist" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-56 animate-pulse rounded-xl bg-white border border-mist"
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({
  search,
  onClear,
}: {
  search: string;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-mist bg-white py-16 px-6 text-center">
      <div className="mb-4">
        <SearchIcon large />
      </div>
      <p className="text-sm font-medium text-forest-dark/70">
        No templates match your search
      </p>
      {search && (
        <p className="mt-1 text-xs text-forest-dark/40">
          Try a different keyword or{" "}
          <button
            onClick={onClear}
            className="text-forest font-medium hover:text-forest-hover"
          >
            clear the search
          </button>
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Inline SVG icons (no external deps)                               */
/* ------------------------------------------------------------------ */

function SearchIcon({ large }: { large?: boolean } = {}) {
  const size = large ? 32 : 16;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      className={large ? "text-forest-dark/20" : "text-forest-dark/30"}
    >
      <path
        d="M7.333 12.667A5.333 5.333 0 1 0 7.333 2a5.333 5.333 0 0 0 0 10.667ZM14 14l-2.9-2.9"
        stroke="currentColor"
        strokeWidth="1.333"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none">
      <path
        d="M12 4 4 12M4 4l8 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StarIcon() {
  return (
    <svg width={10} height={10} viewBox="0 0 16 16" fill="currentColor">
      <path d="M8 .5l2.47 5 5.53.8-4 3.9.94 5.5L8 13.2l-4.94 2.5.94-5.5-4-3.9 5.53-.8L8 .5z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 16 16"
      fill="none"
      className="mt-0.5 shrink-0 text-fern"
    >
      <path
        d="M13.333 4 6 11.333 2.667 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
