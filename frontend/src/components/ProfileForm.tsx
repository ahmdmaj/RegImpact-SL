"use client";

import React, { useState } from "react";
import { BusinessProfile } from "@/services/api";
import { Building2, Sparkles, RotateCcw, Play, Users, Scale, PackageCheck, Globe2, Calendar } from "lucide-react";

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
  const [businessId, setBusinessId] = useState(initialProfile?.business_id || "BIZ-SL-101");
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
      : "unknown"
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
      : "unknown"
  );

  const [asAtDate, setAsAtDate] = useState(initialAsAtDate);

  // Quick Scenario Presets for instant demonstration
  const loadPreset = (type: "compliant" | "incomplete" | "exempt") => {
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
    setBusinessId("BIZ-DEMO-001");
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
      business_id: businessId,
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
    <div className="glass-panel rounded-2xl p-6 border border-slate-700/60 shadow-xl">
      {/* Header & Presets */}
      <div className="flex flex-col gap-3 pb-6 border-b border-slate-700/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-blue-400 font-semibold text-lg">
            <Building2 className="w-5 h-5 text-blue-400" />
            <span>SME Business Profile</span>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Clear</span>
          </button>
        </div>
        <p className="text-xs text-slate-400">
          Fields left blank represent <span className="text-amber-400 font-mono">UNKNOWN</span> in 3-valued Kleene logic.
        </p>

        {/* Quick Scenario Pills */}
        <div className="flex flex-wrap gap-2 pt-1">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Presets:
          </span>
          <button
            type="button"
            onClick={() => loadPreset("compliant")}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-emerald-950/80 text-emerald-300 border border-emerald-700/50 hover:bg-emerald-900/80 transition-all cursor-pointer"
          >
            Scenario 1: Large Manufacturer (FCAU & EPL Apply)
          </button>
          <button
            type="button"
            onClick={() => loadPreset("incomplete")}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-amber-950/80 text-amber-300 border border-amber-700/50 hover:bg-amber-900/80 transition-all cursor-pointer"
          >
            Scenario 2: Missing Capacity (Unknown State)
          </button>
          <button
            type="button"
            onClick={() => loadPreset("exempt")}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-all cursor-pointer"
          >
            Scenario 3: Micro Producer (Under Thresholds)
          </button>
        </div>
      </div>

      {/* Form Fields */}
      <form onSubmit={handleSubmit} className="space-y-4 pt-5">
        {/* Identifier and Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Business ID / Registration Name
            </label>
            <input
              type="text"
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. BIZ-SL-001"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Primary Activity
            </label>
            <select
              value={activity}
              onChange={(e) => setActivity(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-pointer"
            >
              <option value="food_manufacturing">Food Manufacturing (Industrial / Commercial)</option>
              <option value="catering">Catering & Food Service</option>
              <option value="retail">Food Retail & Grocery</option>
              <option value="agriculture">Agricultural Production</option>
            </select>
          </div>
        </div>

        {/* Employees & Production Capacity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-slate-400" />
              <span>Total Employees (CEA EPL Threshold: 20)</span>
            </label>
            <input
              type="number"
              min="0"
              value={employeeCount}
              onChange={(e) => setEmployeeCount(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 placeholder-slate-600"
              placeholder="Leave blank for UNKNOWN"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-slate-400" />
              <span>Production Capacity (FCAU Threshold: 50 kg/day)</span>
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min="0"
                step="any"
                value={capacityValue}
                onChange={(e) => setCapacityValue(e.target.value)}
                className="w-2/3 bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 placeholder-slate-600"
                placeholder="Leave blank for UNKNOWN"
              />
              <select
                value={capacityUnit}
                onChange={(e) => setCapacityUnit(e.target.value)}
                className="w-1/3 bg-slate-900/80 border border-slate-700 rounded-lg px-2 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 cursor-pointer"
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
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <PackageCheck className="w-3.5 h-3.5 text-slate-400" />
              <span>Product Category</span>
            </label>
            <input
              type="text"
              value={productCategory}
              onChange={(e) => setProductCategory(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
              placeholder="e.g. biscuits, tea, dairy, confectionery"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Prepackaged for Retail Sale?
            </label>
            <select
              value={prepackagedState}
              onChange={(e) => setPrepackagedState(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="true">Yes (Prepackaged / Sealed Package)</option>
              <option value="false">No (Sold in bulk / Unpackaged)</option>
              <option value="unknown">Unspecified (UNKNOWN)</option>
            </select>
          </div>
        </div>

        {/* Market Scope & Evaluation Date */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5 text-slate-400" />
              <span>Market Destination</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={marketDomestic}
                onChange={(e) => setMarketDomestic(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 rounded-lg px-2 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="true">Domestic: Yes</option>
                <option value="false">Domestic: No</option>
                <option value="unknown">Domestic: ?</option>
              </select>
              <select
                value={marketExport}
                onChange={(e) => setMarketExport(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 rounded-lg px-2 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="false">Export: No</option>
                <option value="true">Export: Yes</option>
                <option value="unknown">Export: ?</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Evaluation Point-in-Time Date (As-At Date)</span>
            </label>
            <input
              type="date"
              value={asAtDate}
              onChange={(e) => setAsAtDate(e.target.value)}
              className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3 px-6 rounded-xl shadow-lg shadow-blue-500/25 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer glow-blue"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Evaluating 3-Valued Logic Engine...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Analyze Regulatory Impact</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
