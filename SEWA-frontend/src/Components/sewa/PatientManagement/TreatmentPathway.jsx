import React from 'react';
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';
import { cn } from "@/lib/utils";
import { Progress } from "@/Components/ui/progress";

const BUNDLE_ITEMS = [
    { key: 'lactate_measure', label: 'Measure Lactate Level', description: 'Initial measurement within 1 hour' },
    { key: 'blood_cultures', label: 'Obtain Blood Cultures', description: 'Before administering antibiotics' },
    { key: 'antibiotics', label: 'Administer Antibiotics', description: 'Broad spectrum coverage' },
    { key: 'fluids', label: 'Administer IV Fluids', description: '30mL/kg crystalloid for hypotension' },
    { key: 'vasopressors', label: 'Apply Vasopressors', description: 'If hypotensive during/after fluid resuscitation' }
];

export default function TreatmentPathway({ status = {}, onUpdateStatus, riskLevel }) {
    const completedCount = BUNDLE_ITEMS.filter(item => status[item.key]).length;
    const progress = (completedCount / BUNDLE_ITEMS.length) * 100;

    return (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-indigo-50/50">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-indigo-900 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-indigo-600" />
                        Hour-1 Sepsis Bundle
                    </h3>
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-100 px-2.5 py-1 rounded-full">
                        {Math.round(progress)}% Complete
                    </span>
                </div>
                <Progress value={progress} className="h-2 bg-indigo-100" indicatorClassName="bg-indigo-600" />
            </div>

            <div className="p-4 space-y-4">
                {BUNDLE_ITEMS.map((item) => {
                    const isCompleted = status[item.key];
                    return (
                        <button
                            key={item.key}
                            onClick={() => onUpdateStatus(item.key, !isCompleted)}
                            className={cn(
                                "w-full flex items-start gap-3 p-3 rounded-lg border text-left transition-all",
                                isCompleted
                                    ? "bg-emerald-50 border-emerald-200"
                                    : "bg-white border-slate-100 hover:border-indigo-200 hover:shadow-sm"
                            )}
                        >
                            <div className={cn(
                                "mt-0.5",
                                isCompleted ? "text-emerald-600" : "text-slate-300"
                            )}>
                                {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
                            </div>
                            <div>
                                <p className={cn(
                                    "font-medium sm:text-sm text-base",
                                    isCompleted ? "text-emerald-900" : "text-slate-700"
                                )}>
                                    {item.label}
                                </p>
                                <p className={cn(
                                    "text-xs mt-0.5",
                                    isCompleted ? "text-emerald-700/80" : "text-slate-500"
                                )}>
                                    {item.description}
                                </p>
                            </div>
                        </button>
                    );
                })}
            </div>

            {riskLevel === 'HIGH' && progress < 100 && (
                <div className="px-4 pb-4">
                    <div className="bg-red-50 border border-red-100 rounded-lg p-3 text-xs text-red-700 flex gap-2">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <p>High risk patient detected. Complete remaining bundle items immediately.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
