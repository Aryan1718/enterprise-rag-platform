import type { UsageTodayResponse } from "./api";

export type Workspace = {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
};

export type WorkspaceWithUsage = Workspace & {
  usage_today: UsageTodayResponse;
};
