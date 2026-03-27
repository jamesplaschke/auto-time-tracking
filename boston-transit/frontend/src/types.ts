export interface Prediction {
  id: string;
  route_id: string;
  route_name: string | null;
  stop_id: string;
  stop_name: string | null;
  direction_id: number;
  direction_name: string | null;
  arrival_time: string | null;
  departure_time: string | null;
  status: string | null;
}

export interface ServiceAlert {
  id: string;
  header: string;
  description: string;
  severity: number;
  affected_routes: string[];
  affected_stops: string[];
  url: string | null;
}

export interface LeaveNowAlert {
  stop_id: string;
  stop_name: string;
  route_id: string;
  direction_id: number;
  prediction_time: string;
  walk_minutes: number;
  leave_by: string;
  urgency: "now" | "soon" | "upcoming" | "missed";
  minutes_until_leave: number;
}

export interface RouteInfo {
  id: string;
  name: string;
  color: string;
  text_color: string;
  direction_names: string[];
}

export interface StopInfo {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

export interface StopPreference {
  stop_id: string;
  route_id: string;
  walk_minutes: number;
  enabled: boolean;
  label?: string;
}
