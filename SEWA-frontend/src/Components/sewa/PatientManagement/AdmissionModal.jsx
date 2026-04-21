import React, { useState, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/Components/ui/select";
import { Textarea } from "@/Components/ui/textarea";
import { User, Phone, Droplets, HeartPulse, MapPin, Stethoscope, ChevronRight, ChevronLeft } from 'lucide-react';

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const EMPTY_FORM = {
    // Step 1 – Basic Info
    name: '',
    age: '',
    gender: 'Male',
    blood_group: '',
    // Step 2 – Admission Details
    bed_number: '',
    admission_reason: '',
    trajectory: 'stable',
    medical_history: '',
    // Step 3 – Contact & Emergency
    phone: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
};

const STEPS = [
    { label: 'Patient Info', icon: User },
    { label: 'Admission', icon: Stethoscope },
    { label: 'Contact Details', icon: Phone },
];

export default function AdmissionModal({ isOpen, onClose, onAdmit }) {
    const [step, setStep] = useState(0);
    const [formData, setFormData] = useState(EMPTY_FORM);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    // Guard against click-passthrough when Next button is replaced by Submit button
    const justNavigated = useRef(false);
    const justNavigatedTimer = useRef(null);

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) setErrors(prev => ({ ...prev, [field]: '' }));
    };

    const validateStep = () => {
        const newErrors = {};
        if (step === 0) {
            if (!formData.name.trim()) newErrors.name = 'Patient name is required';
            if (!formData.age || isNaN(formData.age) || +formData.age < 0 || +formData.age > 120)
                newErrors.age = 'Enter a valid age (0–120)';
            if (!formData.gender) newErrors.gender = 'Gender is required';
        }
        if (step === 1) {
            if (!formData.bed_number.trim()) newErrors.bed_number = 'Bed number is required';
            if (!formData.admission_reason.trim()) newErrors.admission_reason = 'Admission reason is required';
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleNext = () => {
        if (validateStep()) {
            // Mark that we just navigated so the submit button ignores
            // any residual mouseup/click from the previous Next button click
            justNavigated.current = true;
            if (justNavigatedTimer.current) clearTimeout(justNavigatedTimer.current);
            justNavigatedTimer.current = setTimeout(() => {
                justNavigated.current = false;
            }, 300);
            setStep(s => s + 1);
        }
    };

    const handleBack = () => setStep(s => s - 1);

    const handleSubmit = async (e) => {
        e.preventDefault();
        // Safety guard: only submit when on the last step
        if (step !== STEPS.length - 1) {
            handleNext();
            return;
        }
        if (!validateStep()) return;
        setIsSubmitting(true);
        try {
            await onAdmit({
                ...formData,
                age: parseInt(formData.age),
                medical_history: formData.medical_history
                    .split(',')
                    .map(s => s.trim())
                    .filter(Boolean),
                admission_date: new Date().toISOString(),
            });
            setFormData(EMPTY_FORM);
            setStep(0);
            onClose();
        } finally {
            setIsSubmitting(false);
        }
    };

    // Prevent Enter key from submitting the form prematurely on non-final steps
    const handleFormKeyDown = (e) => {
        if (e.key === 'Enter' && step !== STEPS.length - 1) {
            e.preventDefault();
        }
    };

    const handleClose = () => {
        setFormData(EMPTY_FORM);
        setStep(0);
        setErrors({});
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[520px] p-0 overflow-hidden">
                {/* Header */}
                <DialogHeader className="px-6 pt-6 pb-4 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-slate-200">
                    <DialogTitle className="flex items-center gap-2 text-slate-800">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                            <HeartPulse className="w-4 h-4 text-white" />
                        </div>
                        Admit New Patient
                    </DialogTitle>

                    {/* Step indicator */}
                    <div className="flex items-center gap-1 mt-3">
                        {STEPS.map((s, i) => {
                            const Icon = s.icon;
                            return (
                                <React.Fragment key={i}>
                                    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${i === step
                                        ? 'bg-indigo-600 text-white'
                                        : i < step
                                            ? 'bg-indigo-100 text-indigo-700'
                                            : 'bg-slate-100 text-slate-400'
                                        }`}>
                                        <Icon className="w-3 h-3" />
                                        {s.label}
                                    </div>
                                    {i < STEPS.length - 1 && (
                                        <div className={`h-0.5 flex-1 rounded transition-all ${i < step ? 'bg-indigo-300' : 'bg-slate-200'}`} />
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </div>
                </DialogHeader>

                <form onSubmit={handleSubmit} onKeyDown={handleFormKeyDown}>
                    <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">

                        {/* ── Step 0: Patient Info ── */}
                        {step === 0 && (
                            <>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="col-span-2 space-y-1.5">
                                        <Label htmlFor="name">Full Name <span className="text-red-500">*</span></Label>
                                        <Input
                                            id="name"
                                            placeholder="e.g. Ramesh Kumar"
                                            value={formData.name}
                                            onChange={e => handleChange('name', e.target.value)}
                                            className={errors.name ? 'border-red-400' : ''}
                                        />
                                        {errors.name && <p className="text-xs text-red-500">{errors.name}</p>}
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="age">Age <span className="text-red-500">*</span></Label>
                                        <Input
                                            id="age"
                                            type="number"
                                            min="0"
                                            max="120"
                                            placeholder="e.g. 45"
                                            value={formData.age}
                                            onChange={e => handleChange('age', e.target.value)}
                                            className={errors.age ? 'border-red-400' : ''}
                                        />
                                        {errors.age && <p className="text-xs text-red-500">{errors.age}</p>}
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label>Gender <span className="text-red-500">*</span></Label>
                                        <Select value={formData.gender} onValueChange={val => handleChange('gender', val)}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select gender" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="Male">Male</SelectItem>
                                                <SelectItem value="Female">Female</SelectItem>
                                                <SelectItem value="Other">Other</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="col-span-2 space-y-1.5">
                                        <Label className="flex items-center gap-1.5">
                                            <Droplets className="w-3.5 h-3.5 text-red-500" />
                                            Blood Group
                                        </Label>
                                        <Select value={formData.blood_group} onValueChange={val => handleChange('blood_group', val)}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select blood group" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {BLOOD_GROUPS.map(bg => (
                                                    <SelectItem key={bg} value={bg}>{bg}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* ── Step 1: Admission Details ── */}
                        {step === 1 && (
                            <>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <Label htmlFor="bed">Bed Number <span className="text-red-500">*</span></Label>
                                        <Input
                                            id="bed"
                                            placeholder="e.g. ICU-01"
                                            value={formData.bed_number}
                                            onChange={e => handleChange('bed_number', e.target.value)}
                                            className={errors.bed_number ? 'border-red-400' : ''}
                                        />
                                        {errors.bed_number && <p className="text-xs text-red-500">{errors.bed_number}</p>}
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label>Risk Trajectory</Label>
                                        <Select value={formData.trajectory} onValueChange={val => handleChange('trajectory', val)}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="stable">Stable</SelectItem>
                                                <SelectItem value="early_sepsis">Early Sepsis Risk</SelectItem>
                                                <SelectItem value="rapid_deterioration">Rapid Deterioration</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="col-span-2 space-y-1.5">
                                        <Label htmlFor="reason">Admission Reason <span className="text-red-500">*</span></Label>
                                        <Input
                                            id="reason"
                                            placeholder="e.g. Sepsis, Pneumonia, Post-op Recovery"
                                            value={formData.admission_reason}
                                            onChange={e => handleChange('admission_reason', e.target.value)}
                                            className={errors.admission_reason ? 'border-red-400' : ''}
                                        />
                                        {errors.admission_reason && <p className="text-xs text-red-500">{errors.admission_reason}</p>}
                                    </div>

                                    <div className="col-span-2 space-y-1.5">
                                        <Label htmlFor="history">Medical History</Label>
                                        <Textarea
                                            id="history"
                                            placeholder="Comma separated (e.g. Diabetes, Hypertension, COPD)"
                                            value={formData.medical_history}
                                            onChange={e => handleChange('medical_history', e.target.value)}
                                            rows={3}
                                        />
                                        <p className="text-xs text-slate-400">Separate conditions with commas</p>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* ── Step 2: Contact & Emergency ── */}
                        {step === 2 && (
                            <>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="col-span-2 space-y-1.5">
                                        <Label htmlFor="phone" className="flex items-center gap-1.5">
                                            <Phone className="w-3.5 h-3.5" />
                                            Patient Phone
                                        </Label>
                                        <Input
                                            id="phone"
                                            type="tel"
                                            placeholder="e.g. +91 98765 43210"
                                            value={formData.phone}
                                            onChange={e => handleChange('phone', e.target.value)}
                                        />
                                    </div>

                                    <div className="col-span-2 space-y-1.5">
                                        <Label htmlFor="address" className="flex items-center gap-1.5">
                                            <MapPin className="w-3.5 h-3.5" />
                                            Address
                                        </Label>
                                        <Textarea
                                            id="address"
                                            placeholder="Patient's residential address"
                                            value={formData.address}
                                            onChange={e => handleChange('address', e.target.value)}
                                            rows={2}
                                        />
                                    </div>

                                    <div className="col-span-2 pt-2 border-t border-slate-100">
                                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Emergency Contact</p>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="ecName">Contact Name</Label>
                                        <Input
                                            id="ecName"
                                            placeholder="e.g. Suresh Kumar"
                                            value={formData.emergency_contact_name}
                                            onChange={e => handleChange('emergency_contact_name', e.target.value)}
                                        />
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="ecPhone">Contact Phone</Label>
                                        <Input
                                            id="ecPhone"
                                            type="tel"
                                            placeholder="e.g. +91 98765 00000"
                                            value={formData.emergency_contact_phone}
                                            onChange={e => handleChange('emergency_contact_phone', e.target.value)}
                                        />
                                    </div>
                                </div>
                            </>
                        )}
                    </div>

                    <DialogFooter className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-between gap-2">
                        <Button type="button" variant="outline" onClick={step === 0 ? handleClose : handleBack}>
                            {step === 0 ? 'Cancel' : (
                                <span className="flex items-center gap-1"><ChevronLeft className="w-4 h-4" /> Back</span>
                            )}
                        </Button>

                        {step < STEPS.length - 1 ? (
                            <Button type="button" onClick={handleNext} className="gap-1">
                                Next <ChevronRight className="w-4 h-4" />
                            </Button>
                        ) : (
                            <Button
                                type="button"
                                onClick={(e) => {
                                    // Ignore click if it was triggered by the passthrough
                                    // from clicking the previous "Next" button
                                    if (justNavigated.current) return;
                                    handleSubmit(e);
                                }}
                                disabled={isSubmitting}
                                className="bg-indigo-600 hover:bg-indigo-700 gap-2"
                            >
                                {isSubmitting ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Admitting...
                                    </>
                                ) : (
                                    <>
                                        <HeartPulse className="w-4 h-4" />
                                        Admit Patient
                                    </>
                                )}
                            </Button>
                        )}
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
