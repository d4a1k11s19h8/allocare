
-- ============ ENUMS ============
CREATE TYPE public.app_role AS ENUM ('admin', 'coordinator', 'volunteer');
CREATE TYPE public.issue_type AS ENUM ('food', 'water', 'health', 'housing', 'education', 'safety', 'other');
CREATE TYPE public.urgency_label AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE public.need_status AS ENUM ('open', 'assigned', 'in_progress', 'resolved', 'closed');
CREATE TYPE public.assignment_status AS ENUM ('suggested', 'accepted', 'declined', 'checked_in', 'completed');

-- ============ ORGANIZATIONS ============
CREATE TABLE public.organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  city TEXT DEFAULT 'Mumbai',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ PROFILES ============
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  email TEXT,
  org_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL,
  skills TEXT[] DEFAULT ARRAY[]::TEXT[],
  home_lat DOUBLE PRECISION,
  home_lng DOUBLE PRECISION,
  max_distance_km INT DEFAULT 10,
  available BOOLEAN DEFAULT true,
  hours_contributed INT DEFAULT 0,
  tasks_completed INT DEFAULT 0,
  streak_days INT DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ USER ROLES ============
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  role public.app_role NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);

-- ============ NEED REPORTS ============
CREATE TABLE public.need_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL,
  reporter_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'manual', -- manual, csv, ocr, whatsapp
  raw_text TEXT NOT NULL,
  language_detected TEXT DEFAULT 'en',
  zone TEXT NOT NULL,
  location_text TEXT,
  lat DOUBLE PRECISION NOT NULL,
  lng DOUBLE PRECISION NOT NULL,
  issue_type public.issue_type NOT NULL DEFAULT 'other',
  severity_score INT NOT NULL DEFAULT 5 CHECK (severity_score BETWEEN 1 AND 10),
  affected_count INT,
  summary TEXT,
  required_skills TEXT[] DEFAULT ARRAY[]::TEXT[],
  recommended_volunteer_count INT DEFAULT 1,
  urgency_score INT NOT NULL DEFAULT 0 CHECK (urgency_score BETWEEN 0 AND 100),
  urgency_label public.urgency_label NOT NULL DEFAULT 'LOW',
  status public.need_status NOT NULL DEFAULT 'open',
  first_reported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_needs_status ON public.need_reports(status);
CREATE INDEX idx_needs_urgency ON public.need_reports(urgency_score DESC);
CREATE INDEX idx_needs_zone_issue ON public.need_reports(zone, issue_type);

-- ============ ASSIGNMENTS ============
CREATE TABLE public.assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  need_id UUID NOT NULL REFERENCES public.need_reports(id) ON DELETE CASCADE,
  volunteer_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  match_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  distance_km DOUBLE PRECISION,
  explanation TEXT,
  status public.assignment_status NOT NULL DEFAULT 'suggested',
  accepted_at TIMESTAMPTZ,
  checked_in_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  proof_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (need_id, volunteer_id)
);
CREATE INDEX idx_assignments_volunteer ON public.assignments(volunteer_id);
CREATE INDEX idx_assignments_need ON public.assignments(need_id);

-- ============ has_role security definer ============
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role public.app_role)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;

-- ============ updated_at trigger ============
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_profiles_updated BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_needs_updated BEFORE UPDATE ON public.need_reports
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============ profile auto-create on signup ============
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, email)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    NEW.email
  );
  -- Default role: volunteer
  INSERT INTO public.user_roles (user_id, role)
  VALUES (NEW.id, 'volunteer');
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============ ENABLE RLS ============
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.need_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;

-- ============ RLS POLICIES ============
-- Organizations: readable by everyone (public directory)
CREATE POLICY "orgs readable" ON public.organizations FOR SELECT USING (true);
CREATE POLICY "orgs admin write" ON public.organizations FOR ALL TO authenticated
  USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- Profiles: own profile read/write; coordinators read all (for matching)
CREATE POLICY "profiles read own" ON public.profiles FOR SELECT TO authenticated
  USING (id = auth.uid() OR public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'));
CREATE POLICY "profiles update own" ON public.profiles FOR UPDATE TO authenticated
  USING (id = auth.uid()) WITH CHECK (id = auth.uid());
CREATE POLICY "profiles insert own" ON public.profiles FOR INSERT TO authenticated
  WITH CHECK (id = auth.uid());

-- User roles: read own; admins manage
CREATE POLICY "roles read own" ON public.user_roles FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.has_role(auth.uid(), 'admin') OR public.has_role(auth.uid(), 'coordinator'));
CREATE POLICY "roles admin manage" ON public.user_roles FOR ALL TO authenticated
  USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- Need reports: any authenticated user can read; coordinators+volunteers can insert; coordinators update
CREATE POLICY "needs read all auth" ON public.need_reports FOR SELECT TO authenticated USING (true);
CREATE POLICY "needs public read" ON public.need_reports FOR SELECT TO anon USING (true);
CREATE POLICY "needs insert auth" ON public.need_reports FOR INSERT TO authenticated
  WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY "needs update coordinator" ON public.need_reports FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'))
  WITH CHECK (public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'));

-- Assignments: volunteer sees own; coordinators see all; coordinators/system create
CREATE POLICY "assign read own or coord" ON public.assignments FOR SELECT TO authenticated
  USING (volunteer_id = auth.uid() OR public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'));
CREATE POLICY "assign insert coord" ON public.assignments FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin') OR volunteer_id = auth.uid());
CREATE POLICY "assign update self or coord" ON public.assignments FOR UPDATE TO authenticated
  USING (volunteer_id = auth.uid() OR public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'))
  WITH CHECK (volunteer_id = auth.uid() OR public.has_role(auth.uid(), 'coordinator') OR public.has_role(auth.uid(), 'admin'));
