"use client";

import React, { useState } from "react";
import { BusinessProfile } from "@/services/api";
import { ScenarioPresetCards, PresetScenarioType } from "./ScenarioPresetCards";
import { 
  Building2, 
  RotateCcw, 
  Play, 
  Users, 
  Scale, 
  PackageCheck, 
  Globe2, 
  Calendar,
  Store,
  Tag
} from "lucide-react";

interface ProfileFormProps {
  initialProfile?: BusinessProfile;
  initialAsAtDate?: string;
  onAnalyze: (profile: BusinessProfile, asAtDate: string) => void;
  isLoading: boolean;
}

export const ProfileForm: React.FC<ProfileFormProps> = ({
  initialProfile,
  initialAsAtDate = "2026-08-01",
  onAnalyze,
  isLoading,
}) => {
  const [activePreset, setActivePreset] = useState<PresetScenarioType | null>("retail");
  const [businessId, setBusinessId] = useState(initialProfile?.business_id || "BIZ-SL-RETAIL-01");
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
    initialProfile?.products?.[0]?.category || "Bottled Mixed Fruit Jam"
  );
  const [prepackagedState, setPrepackagedState] = useState<string>(
    initialProfile?.products?.[0]?.prepackaged === true
      ? "true"
      : initialProfile?.products?.[0]?.prepackaged === false
      ? "false"
      : "true"
  );

  const [marketChannel, setMarketChannel] = useState<"retail" | "b2b" | "unknown">("retail");
  const [purchaserPresent, setPurchaserPresent] = useState<"false" | "true" | "unknown">("false");

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
  const handleSelectPreset = (type: PresetScenarioType) => {
    setActivePreset(type);
    if (type === "retail") {
      setBusinessId("BIZ-SL-RETAIL-01");
      setActivity("food_manufacturing");
      setEmployeeCount("25");
      setCapacityValue("100");
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("Bottled Mixed Fruit Jam");
      setPrepackagedState("true");
      setPurchaserPresent("false");
      setMarketChannel("retail");
      setMarketDomestic("true");
      setMarketExport("false");
      setAsAtDate("2026-08-01");
    } else if (type === "b2b") {
      setBusinessId("BIZ-SL-B2B-01");
      setActivity("food_manufacturing");
      setEmployeeCount("40");
      setCapacityValue("500");
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("Industrial Bulk Mango Puree (200L Drum)");
      setPrepackagedState("true");
      setPurchaserPresent("false");
      setMarketChannel("b2b");
      setMarketDomestic("true");
      setMarketExport("false");
      setAsAtDate("2026-08-01");
    } else if (type === "incomplete") {
      setBusinessId("BIZ-SL-UNKNOWN-CHANNEL");
      setActivity("food_manufacturing");
      setEmployeeCount("15");
      setCapacityValue("80");
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("Bakery Goods");
      setPrepackagedState("true");
      setPurchaserPresent("false");
      setMarketChannel("unknown");
      setMarketDomestic("unknown");
      setMarketExport("unknown");
      setAsAtDate("2026-08-01");
    } else if (type === "exempt") {
      setBusinessId("BIZ-SL-OVER-COUNTER");
      setActivity("food_manufacturing");
      setEmployeeCount("5");
      setCapacityValue("20");
      setCapacityUnit("kg");
      setCapacityPeriod("day");
      setProductCategory("Traditional Fresh Sweets");
      setPrepackagedState("false");
      setPurchaserPresent("true");
      setMarketChannel("retail");
      setMarketDomestic("true");
      setMarketExport("false");
      setAsAtDate("2026-08-01");
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
    setPurchaserPresent("unknown");
    setMarketChannel("unknown");
    setMarketDomestic("unknown");
    setMarketExport("unknown");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const empCountNum = employeeCount.trim() === "" ? null : Number(employeeCount);
    const capNum = capacityValue.trim() === "" ? null : Number(capacityValue);

    // Build market object: if all subfields are unknown, pass null so Kleene logic detects missing data
    let marketObj: any = null;
    if (marketChannel !== "unknown" || marketDomestic !== "unknown" || marketExport !== "unknown") {
      marketObj = {
        domestic: marketDomestic === "true" ? true : marketDomestic === "false" ? false : null,
        export_flag: marketExport === "true" ? true : marketExport === "false" ? false : null,
        b2b_only: marketChannel === "b2b" ? true : marketChannel === "retail" ? false : null,
      };
    }

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
          product_name: productCategory,
          category: productCategory,
          prepackaged: prepackagedState === "true" ? true : prepackagedState === "false" ? false : null,
        }
      ] : [],
      market: marketObj,
      packaged_in_presence_of_purchaser: purchaserPresent === "true" ? true : purchaserPresent === "false" ? false : null,
    };

    onAnalyze(profile, asAtDate);
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-800 text-zinc-300 border border-zinc-700">
            <Building2 className="w-4 h-4 text-zinc-300" />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-zinc-100">
              Manufacturer Profile
            </h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Specify enterprise parameters to evaluate statutory rules under Kleene 3-valued logic.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-1.5 px-2 py-1 text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
          title="Clear inputs"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset</span>
        </button>
      </div>

      {/* Preset Cards */}
      <ScenarioPresetCards
        onSelectPreset={handleSelectPreset}
        activePreset={activePreset}
      />

      {/* Form Fields */}
      <form onSubmit={handleSubmit} className="space-y-4 pt-1">
        {/* Identifier and Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              Registration / Business ID
            </label>
            <input
              type="text"
              value={businessId}
              onChange={(e) => {
                setActivePreset(null);
                setBusinessId(e.target.value);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 transition-colors"
              placeholder="e.g. BIZ-COLOMBO-FOODS"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              Primary Activity
            </label>
            <select
              value={activity}
              onChange={(e) => {
                setActivePreset(null);
                setActivity(e.target.value);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 cursor-pointer transition-colors"
            >
              <option value="food_manufacturing">Food Manufacturing (Industrial / Commercial)</option>
              <option value="catering">Catering & Food Service</option>
              <option value="retail">Food Retail & Grocery</option>
              <option value="agriculture">Agricultural Production</option>
            </select>
          </div>
        </div>

        {/* Workforce & Production Capacity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-zinc-500" />
                <span>Total Employees</span>
              </span>
              <span className="text-[10px] font-mono text-zinc-500">&ge; 20 (EPL)</span>
            </label>
            <input
              type="number"
              min="0"
              value={employeeCount}
              onChange={(e) => {
                setActivePreset(null);
                setEmployeeCount(e.target.value);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 transition-colors"
              placeholder="Leave blank for UNKNOWN"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-zinc-500" />
                <span>Daily Capacity</span>
              </span>
              <span className="text-[10px] font-mono text-zinc-500">&ge; 50 kg/day (FCAU)</span>
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
                className="w-2/3 h-9 bg-zinc-950 border border-zinc-800 rounded-md px-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 transition-colors"
                placeholder="Leave blank for UNKNOWN"
              />
              <select
                value={capacityUnit}
                onChange={(e) => setCapacityUnit(e.target.value)}
                className="w-1/3 h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 cursor-pointer"
              >
                <option value="kg">kg / day</option>
                <option value="metric_tons">tons / day</option>
                <option value="litres">litres / day</option>
              </select>
            </div>
          </div>
        </div>

        {/* Product Category & Prepackaging */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center gap-1.5">
              <PackageCheck className="w-3.5 h-3.5 text-zinc-500" />
              <span>Product Category</span>
            </label>
            <input
              type="text"
              value={productCategory}
              onChange={(e) => {
                setActivePreset(null);
                setProductCategory(e.target.value);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 transition-colors"
              placeholder="e.g. biscuits, tea, dairy, spices"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              Packaging Format
            </label>
            <select
              value={prepackagedState}
              onChange={(e) => {
                setActivePreset(null);
                setPrepackagedState(e.target.value);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 focus:border-zinc-500 cursor-pointer"
            >
              <option value="true">Prepackaged / Sealed for Retail Sale</option>
              <option value="false">Unpackaged / Bulk Sale Only</option>
              <option value="unknown">Unspecified (UNKNOWN)</option>
            </select>
          </div>
        </div>

        {/* Market Channel & Purchaser Presence (Gazette 2494/47 Regulation 3) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5 text-zinc-500" />
              <span>Market Distribution Channel</span>
            </label>
            <select
              value={marketChannel}
              onChange={(e) => {
                setActivePreset(null);
                setMarketChannel(e.target.value as any);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 cursor-pointer"
            >
              <option value="retail">Retail Consumer Channel (b2b_only = false)</option>
              <option value="b2b">B2B Wholesale Only (b2b_only = true)</option>
              <option value="unknown">Unspecified (UNKNOWN - Kleene Missing Data)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-zinc-500" />
              <span>Packaged in Front of Purchaser</span>
            </label>
            <select
              value={purchaserPresent}
              onChange={(e) => {
                setActivePreset(null);
                setPurchaserPresent(e.target.value as any);
              }}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 cursor-pointer"
            >
              <option value="false">No — Prepackaged at facility (Standard Mandate)</option>
              <option value="true">Yes — Packaged in presence of purchaser (Exempt)</option>
              <option value="unknown">Unspecified (UNKNOWN)</option>
            </select>
          </div>
        </div>

        {/* Market Destination & As-At Date */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center gap-1.5">
              <Globe2 className="w-3.5 h-3.5 text-zinc-500" />
              <span>Geographic Destination</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={marketDomestic}
                onChange={(e) => setMarketDomestic(e.target.value)}
                className="h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 cursor-pointer"
              >
                <option value="true">Domestic: Yes</option>
                <option value="false">Domestic: No</option>
                <option value="unknown">Domestic: ?</option>
              </select>
              <select
                value={marketExport}
                onChange={(e) => setMarketExport(e.target.value)}
                className="h-9 bg-zinc-950 border border-zinc-800 rounded-md px-2 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 cursor-pointer"
              >
                <option value="false">Export: No</option>
                <option value="true">Export: Yes</option>
                <option value="unknown">Export: ?</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-zinc-500" />
              <span>Evaluation Point-in-Time Date</span>
            </label>
            <input
              type="date"
              value={asAtDate}
              onChange={(e) => setAsAtDate(e.target.value)}
              className="w-full h-9 bg-zinc-950 border border-zinc-800 rounded-md px-3 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Primary Action Button: High-Contrast Crisp White Vercel/Linear Style */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-10 flex items-center justify-center gap-2 bg-white hover:bg-zinc-200 text-zinc-950 font-medium text-xs rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-zinc-900/30 border-t-zinc-900 rounded-full animate-spin" />
                <span>Evaluating Logic Engine...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-zinc-950 text-zinc-950" />
                <span>Analyze Regulatory Impact</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
