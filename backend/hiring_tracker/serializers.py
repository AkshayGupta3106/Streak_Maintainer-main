"""
hiring_tracker/api/serializers.py
"""

from rest_framework import serializers

from hiring_tracker.models import Company, HiringSeason, Opportunity


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id", "name", "slug", "company_type",
            "career_portal_base_url", "logo_url", "is_active",
        ]


class HiringSeasonSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = HiringSeason
        fields = [
            "id", "company_name", "name", "opportunity_type",
            "recurrence_pattern", "typical_window_start_month",
            "typical_window_end_month",
        ]


class OpportunitySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_type = serializers.CharField(source="company.company_type", read_only=True)
    logo_url = serializers.URLField(source="company.logo_url", read_only=True)
    season_name = serializers.CharField(source="hiring_season.name", read_only=True, default=None)

    # Computed fields — never stored, always fresh
    days_until_hiring = serializers.SerializerMethodField()
    urgency_section = serializers.SerializerMethodField()
    urgency_color = serializers.SerializerMethodField()
    is_active_now = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "company_name", "company_type", "logo_url",
            "role", "opportunity_type", "season_name",
            "expected_registration_start", "expected_registration_end",
            "expected_hiring_window_start", "expected_hiring_window_end",
            "career_portal_link", "notes",
            "priority_level", "status",
            "source", "source_url", "is_date_confirmed",
            # computed
            "days_until_hiring", "urgency_section", "urgency_color", "is_active_now",
            "created_at", "updated_at",
        ]

    def get_days_until_hiring(self, obj):
        return obj.days_until_hiring()

    def get_urgency_section(self, obj):
        section, _ = obj.urgency_bucket()
        return section

    def get_urgency_color(self, obj):
        _, color = obj.urgency_bucket()
        return color

    def get_is_active_now(self, obj):
        return obj.is_currently_active()


class OpportunityWriteSerializer(serializers.ModelSerializer):
    """Used for POST/PATCH — strips computed read-only fields."""
    class Meta:
        model = Opportunity
        fields = [
            "company", "hiring_season", "role", "opportunity_type",
            "expected_registration_start", "expected_registration_end",
            "expected_hiring_window_start", "expected_hiring_window_end",
            "career_portal_link", "notes", "priority_level", "status",
            "source", "source_url", "is_date_confirmed",
        ]
