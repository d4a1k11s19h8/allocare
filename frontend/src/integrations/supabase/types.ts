export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      assignments: {
        Row: {
          accepted_at: string | null
          checked_in_at: string | null
          completed_at: string | null
          created_at: string
          distance_km: number | null
          explanation: string | null
          id: string
          match_score: number
          need_id: string
          proof_url: string | null
          status: Database["public"]["Enums"]["assignment_status"]
          volunteer_id: string
        }
        Insert: {
          accepted_at?: string | null
          checked_in_at?: string | null
          completed_at?: string | null
          created_at?: string
          distance_km?: number | null
          explanation?: string | null
          id?: string
          match_score?: number
          need_id: string
          proof_url?: string | null
          status?: Database["public"]["Enums"]["assignment_status"]
          volunteer_id: string
        }
        Update: {
          accepted_at?: string | null
          checked_in_at?: string | null
          completed_at?: string | null
          created_at?: string
          distance_km?: number | null
          explanation?: string | null
          id?: string
          match_score?: number
          need_id?: string
          proof_url?: string | null
          status?: Database["public"]["Enums"]["assignment_status"]
          volunteer_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "assignments_need_id_fkey"
            columns: ["need_id"]
            isOneToOne: false
            referencedRelation: "need_reports"
            referencedColumns: ["id"]
          },
        ]
      }
      need_reports: {
        Row: {
          affected_count: number | null
          created_at: string
          first_reported_at: string
          id: string
          issue_type: Database["public"]["Enums"]["issue_type"]
          language_detected: string | null
          lat: number
          lng: number
          location_text: string | null
          org_id: string | null
          raw_text: string
          recommended_volunteer_count: number | null
          reporter_id: string | null
          required_skills: string[] | null
          severity_score: number
          source: string
          status: Database["public"]["Enums"]["need_status"]
          summary: string | null
          updated_at: string
          urgency_label: Database["public"]["Enums"]["urgency_label"]
          urgency_score: number
          zone: string
        }
        Insert: {
          affected_count?: number | null
          created_at?: string
          first_reported_at?: string
          id?: string
          issue_type?: Database["public"]["Enums"]["issue_type"]
          language_detected?: string | null
          lat: number
          lng: number
          location_text?: string | null
          org_id?: string | null
          raw_text: string
          recommended_volunteer_count?: number | null
          reporter_id?: string | null
          required_skills?: string[] | null
          severity_score?: number
          source?: string
          status?: Database["public"]["Enums"]["need_status"]
          summary?: string | null
          updated_at?: string
          urgency_label?: Database["public"]["Enums"]["urgency_label"]
          urgency_score?: number
          zone: string
        }
        Update: {
          affected_count?: number | null
          created_at?: string
          first_reported_at?: string
          id?: string
          issue_type?: Database["public"]["Enums"]["issue_type"]
          language_detected?: string | null
          lat?: number
          lng?: number
          location_text?: string | null
          org_id?: string | null
          raw_text?: string
          recommended_volunteer_count?: number | null
          reporter_id?: string | null
          required_skills?: string[] | null
          severity_score?: number
          source?: string
          status?: Database["public"]["Enums"]["need_status"]
          summary?: string | null
          updated_at?: string
          urgency_label?: Database["public"]["Enums"]["urgency_label"]
          urgency_score?: number
          zone?: string
        }
        Relationships: [
          {
            foreignKeyName: "need_reports_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      organizations: {
        Row: {
          city: string | null
          created_at: string
          id: string
          name: string
          slug: string
        }
        Insert: {
          city?: string | null
          created_at?: string
          id?: string
          name: string
          slug: string
        }
        Update: {
          city?: string | null
          created_at?: string
          id?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          available: boolean | null
          created_at: string
          email: string | null
          full_name: string
          home_lat: number | null
          home_lng: number | null
          hours_contributed: number | null
          id: string
          max_distance_km: number | null
          org_id: string | null
          skills: string[] | null
          streak_days: number | null
          tasks_completed: number | null
          updated_at: string
        }
        Insert: {
          available?: boolean | null
          created_at?: string
          email?: string | null
          full_name: string
          home_lat?: number | null
          home_lng?: number | null
          hours_contributed?: number | null
          id: string
          max_distance_km?: number | null
          org_id?: string | null
          skills?: string[] | null
          streak_days?: number | null
          tasks_completed?: number | null
          updated_at?: string
        }
        Update: {
          available?: boolean | null
          created_at?: string
          email?: string | null
          full_name?: string
          home_lat?: number | null
          home_lng?: number | null
          hours_contributed?: number | null
          id?: string
          max_distance_km?: number | null
          org_id?: string | null
          skills?: string[] | null
          streak_days?: number | null
          tasks_completed?: number | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "profiles_org_id_fkey"
            columns: ["org_id"]
            isOneToOne: false
            referencedRelation: "organizations"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
    }
    Enums: {
      app_role: "admin" | "coordinator" | "volunteer"
      assignment_status:
        | "suggested"
        | "accepted"
        | "declined"
        | "checked_in"
        | "completed"
      issue_type:
        | "food"
        | "water"
        | "health"
        | "housing"
        | "education"
        | "safety"
        | "other"
      need_status: "open" | "assigned" | "in_progress" | "resolved" | "closed"
      urgency_label: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "coordinator", "volunteer"],
      assignment_status: [
        "suggested",
        "accepted",
        "declined",
        "checked_in",
        "completed",
      ],
      issue_type: [
        "food",
        "water",
        "health",
        "housing",
        "education",
        "safety",
        "other",
      ],
      need_status: ["open", "assigned", "in_progress", "resolved", "closed"],
      urgency_label: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    },
  },
} as const
