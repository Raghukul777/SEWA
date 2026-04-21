import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/Components/ui/dialog";
import { Button } from "@/Components/ui/button";
import { Input } from "@/Components/ui/input";
import { Label } from "@/Components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/Components/ui/select";
import { Textarea } from "@/Components/ui/textarea";

export default function DischargeModal({ isOpen, onClose, onDischarge, patientName }) {
    const [formData, setFormData] = useState({
        diagnosis: '',
        outcome: 'Discharged Home',
        summary: '',
        followUp: ''
    });

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onDischarge(formData);

        // Reset form
        setFormData({
            diagnosis: '',
            outcome: 'Discharged Home',
            summary: '',
            followUp: ''
        });
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Discharge Patient</DialogTitle>
                    <DialogDescription>
                        Complete discharge summary for {patientName}. This data will be used to train our prediction models.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="diagnosis">Final Diagnosis</Label>
                        <Input
                            id="diagnosis"
                            required
                            placeholder="e.g. Sepsis resolved, Community Acquired Pneumonia"
                            value={formData.diagnosis}
                            onChange={(e) => handleChange('diagnosis', e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="outcome">Discharge Outcome</Label>
                        <Select
                            value={formData.outcome}
                            onValueChange={(val) => handleChange('outcome', val)}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select outcome" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="Discharged Home">Discharged Home</SelectItem>
                                <SelectItem value="Transferred to Ward">Transferred to Ward</SelectItem>
                                <SelectItem value="Transferred to Other Facility">Transferred to Other Facility</SelectItem>
                                <SelectItem value="Deceased">Deceased</SelectItem>
                                <SelectItem value="AMA">Left Against Medical Advice</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="summary">Clinical Summary</Label>
                        <Textarea
                            id="summary"
                            required
                            className="min-h-[100px]"
                            placeholder="Brief summary of hospital course and treatment response..."
                            value={formData.summary}
                            onChange={(e) => handleChange('summary', e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="followUp">Follow-up Instructions</Label>
                        <Input
                            id="followUp"
                            placeholder="e.g. Follow up with PCP in 1 week"
                            value={formData.followUp}
                            onChange={(e) => handleChange('followUp', e.target.value)}
                        />
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
                        <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700">Confirm Discharge</Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
