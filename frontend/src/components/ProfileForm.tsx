"use client";

import React, { useState } from "react";
import { BusinessProfile } from "@/services/api";
import { ScenarioPresetCards } from "./ScenarioPresetCards";
import { 
  Building2, 
  RotateCcw, 
  Play, 
  Users, 
  Scale, 
  PackageCheck, 
  Globe2, 
  Calendar 
} from "lucide-react";

interface ProfileFormProps {
  initialProfile?: BusinessProfile;
  initialAsAtDate?: string;
  onAnalyze: (profile: BusinessProfile, asAtDate: string) => void;
  isLoading: boolean;
}

export const ProfileForm: React.FC<ProfileFormProps> = ({
  initialProfile,
  initialAsAtDate = "2024-08-01",
  onAnalyze,
  isLoading,
}) => {
  const [activePreset, setActivePreset] = useState<"compliant" | "incomplete" | "exempt" | null>("compliant");
  const [businessId, setBusinessId] = useState(initialProfile?.business_id || "BIZ-COLOMBO-FOODS");
  const [activity, setActivity] = useState(initialProfile?.activity || "food_manufacturing");
  const [employeeCount, setEmployeeCount] = useState<string>(
    initialProfile?.employee_count !== undefined && initialProfile?.employee_count !== null
      ? String(initialProfile.employee_count)
      : "25"
  );
  const [capacityValue, setCapacityValue] = useState<string>(
    initialProfile?.production_capacity?.value !== undefined && initialProfile?.production_capacity?.value !== null
      ? String(initialProfile.production_capacity.value)
      : "100"
  );
  const [capacityUnit, setCapacityUnit] = useState(initialProfile?.production_capacity?.unit || "kg");
  const [capacityPeriod, setCapacityPeriod] = useState(initialProfile?.production_capacity?.per_period || "day");
  
  const [productCategory, setProductCategory] = useState(
    initialProfile?.products?.[0]?.category || "biscuits"
  );
  const [prepackagedState, setPrepackagedState] = useState<string>(
    initialProfile?.products?.[0]?.prepackaged === true
      ? "true"
      : initialProfile?.products?.[0]?.prepackaged === false
      ? "false"
      : "true"
  );

  const [marketDomestic, setMarketDomestic] = useState<string>(
    initialProfile?.market?.domestic === true
      ? "true"
      : initialProfile?.market?.domestic === false
      ? "false"
      : "true"
  );
  const [marketExport, setMarketExport] = useState<string>(
    initialProfile?.market?.export_flag === true
      ? "true"
      : initialProfile?.market?.export_flag === false
      ? "false"
      : "false"
  );

  const [asAtDate, setAsAtDate] = useState(initialAsAtDate);

  // Load Preset
  const handleSelectPreset = (type: "compliant" | "incomplete" | "exempt") => {
    setActivePreset(type);
    if (type === "compliant") {
      setBusinessId("BIZ-COLOMBO-FOODS");
      setActivity("food_manufacturing");
      setEmployeeCount("25"); // >= 20 triggers CEA EPL
      setCapacityValue("100"); // >= 50 kg/day triggers FCAU labelling
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("biscuits");
      setPrepackagedState("true");
      setMarketDomestic("true");
      setMarketExport("false");
      setAsAtDate("2024-08-01");
    } else if (type === "incomplete") {
      setBusinessId("BIZ-KANDY-BAKERY");
      setActivity("food_manufacturing");
      setEmployeeCount("15");
      setCapacityValue(""); // Empty triggers CONDITIONAL_MISSING_DATA (Kleene UNKNOWN)
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("bread_and_pastry");
      setPrepackagedState("true");
      setMarketDomestic("true");
      setMarketExport("unknown");
      setAsAtDate("2024-08-01");
    } else if (type === "exempt") {
      setBusinessId("BIZ-GALLE-COTTAGE");
      setActivity("food_manufacturing");
      setEmployeeCount("8"); // < 20 employees
      setCapacityValue("30"); // < 50 kg/day
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("traditional_sweets");
      setPrepackagedState("false");
      setMarketDomestic("true");
      setMarketExport("false");
      setAsAtDate("2024-08-01");
    }
  };

  const handleReset = () => {
    setActivePreset(null);
    setBusinessId("");
    setActivity("food_manufacturing");
    setEmployeeCount("");
    setCapacityValue("");
    setProductCategory("");
    setPrepackagedState("unknown");
    setMarketDomestic("unknown");
    setMarketExport("unknown");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const empCountNum = employeeCount.trim() === "" ? null : Number(employeeCount);
    const capNum = capacityValue.trim() === "" ? null : Number(capacityValue);

    const profile: BusinessProfile = {
      business_id: businessId.trim() || "BIZ-SL-CUSTOM",
      activity: activity.trim() || null,
      industry: "food_and_beverage",
      employee_count: empCountNum,
      production_capacity: capNum !== null ? {
        value: capNum,
        unit: capacityUnit,
        per_period: capacityPeriod,
      } : null,
      products: productCategory ? [
        {
          category: productCategory,
          prepackaged: prepackagedState === "true" ? true : prepackagedState === "false" ? false : null,
        }
      ] : [],
      market: {
        domestic: marketDomestic === "true" ? true : marketDomestic === "false" ? false : null,
        export_flag: marketExport === "true" ? true : marketExport === "false" ? false : null,
      },
    };

    onAnalyze(profile, asAtDate);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 shadow-sm p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
            <Building2 className="w-4 h-4 text-slate-300" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">
              Food Manufacturer Profile
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Specify enterprise parameters to evaluate statutory applicability under Kleene 3-valued logic.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition-colors"
          title="Clear all inputs"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      </div>

      {/* Preset Cards */}
      <ScenarioPresetCards
        onSelectPreset={handleSelectPreset}
        activePreset={activePreset}
      />

      {/* Form Fields */}
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {/* Identifier and Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Registration / Business ID
            </label>
            <input
              type="text"
              value={businessId}
              onChange={(e) => {
                setActivePreset(null);
                setBusinessId(e.target.value);
              }}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors"
              placeholder="e.g. BIZ-COLOMBO-FOODS"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Primary Industrial Activity
            </label>
            <select
              value={activity}
              onChange={(e) => {
                setActivePreset(null);
                setActivity(e.target.value);
              }}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 cursor-pointer transition-colors"
            >
              <option value="food_manufacturing">Food Manufacturing (Industrial / Commercial)</option>
              <option value="catering">Catering & Food Service</option>
              <option value="retail">Food Retail & Grocery</option>
              <option value="agriculture">Agricultural Production</option>
            </select>
          </div>
        </div>

        {/* Workforce & Production Capacity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-slate-400" />
                <span>Total Employees</span>
              </span>
              <span className="text-[11px] font-mono text-slate-500">Threshold: 20 (EPL)</span>
            </label>
            <input
              type="number"
              min="0"
              value={employeeCount}
              onChange={(e) => {
                setActivePreset(null);
                setEmployeeCount(e.target.value);
              }}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors placeholder:text-slate-600"
              placeholder="Leave blank for UNKNOWN"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-slate-400" />
                <span>Daily Capacity</span>
              </span>
              <span className="text-[11px] font-mono text-slate-500">Threshold: 50 kg/day (FCAU)</span>
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min="0"
                step="any"
                value={capacityValue}
                onChange={(e) => {
                  setActivePreset(null);
                  setCapacityValue(e.target.value);
                }}
                className="w-2/3 h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors placeholder:text-slate-600"
                placeholder="Leave blank for UNKNOWN"
              />
              <select
                value={capacityUnit}
                onChange={(e) => setCapacityUnit(e.target.value)}
                className="w-1/3 h-10 bg-slate-950 border border-slate-800 rounded-lg px-2 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 cursor-pointer"
              >
                <option value="kg">kg / day</option>
                <option value="metric_tons">tons / day</option>
                <option value="litres">litres / day</option>
              </select>
            </div>
          </div>
        </div>

        {/* Product Category & Prepackaging */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
              <PackageCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>Product Category</span>
            </label>
            <input
              type="text"
              value={productCategory}
              onChange={(e) => {
                setActivePreset(null);
                setProductCategory(e.target.value);
              }}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 transition-colors"
              placeholder="e.g. biscuits, tea, dairy, spices"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Packaging Format
            </label>
            <select
              value={prepackagedState}
              onChange={(e) => {
                setActivePreset(null);
                setPrepackagedState(e.target.value);
              }}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 cursor-pointer"
            >
              <option value="true">Prepackaged / Sealed for Retail Sale</option>
              <option value="false">Unpackaged / Bulk Sale Only</option>
              <option value="unknown">Unspecified (UNKNOWN)</option>
            </select>
          </div>
        </div>

        {/* Market Destination & As-At Date */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5 text-slate-400" />
              <span>Market Destination Scope</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={marketDomestic}
                onChange={(e) => setMarketDomestic(e.target.value)}
                className="h-10 bg-slate-950 border border-slate-800 rounded-lg px-2 text-xs text-slate-100 focus:outline-none focus:border-slate-500 cursor-pointer"
              >
                <option value="true">Domestic: Yes</option>
                <option value="false">Domestic: No</option>
                <option value="unknown">Domestic: Unknown</option>
              </select>
              <select
                value={marketExport}
                onChange={(e) => setMarketExport(e.target.value)}
                className="h-10 bg-slate-950 border border-slate-800 rounded-lg px-2 text-xs text-slate-100 focus:outline-none focus:border-slate-500 cursor-pointer"
              >
                <option value="false">Export: No</option>
                <option value="true">Export: Yes</option>
                <option value="unknown">Export: Unknown</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Evaluation Point-in-Time Date (Temporal Validity)</span>
            </label>
            <input
              type="date"
              value={asAtDate}
              onChange={(e) => setAsAtDate(e.target.value)}
              className="w-full h-10 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-100 focus:outline-none focus:border-slate-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Submit Action */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-11 flex items-center justify-center gap-2 bg-slate-100 hover:bg-white text-slate-900 font-semibold text-xs rounded-lg transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin" />
                <span>Evaluating Neuro-Symbolic Engine...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-slate-900 text-slate-900" />
                <span>Run Regulatory Compliance Analysis</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
