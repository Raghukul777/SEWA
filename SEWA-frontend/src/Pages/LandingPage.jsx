import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Activity, ShieldCheck, Zap, BarChart3, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function LandingPage() {
    // Animation Variants
    const fadeIn = {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.5 }
    };

    const stagger = {
        animate: { transition: { staggerChildren: 0.1 } }
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans selection:bg-blue-100">
            {/* Navigation */}
            <nav className="border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-2">
                            <div className="bg-blue-600 p-1.5 rounded-lg shadow-md shadow-blue-100">
                                <Activity className="w-6 h-6 text-white" />
                            </div>
                            <span className="text-2xl font-black text-slate-900 tracking-tighter">
                                SEWA
                            </span>
                        </div>
                        <div className="hidden md:flex items-center gap-10">
                            <nav className="flex items-center gap-8">
                                <a href="#features" className="text-sm font-bold text-slate-500 hover:text-blue-600 transition-colors">Features</a>
                                <a href="#about" className="text-sm font-bold text-slate-500 hover:text-blue-600 transition-colors">About</a>
                            </nav>
                            <div className="flex items-center gap-4">
                                <Link to="/login">
                                    <Button variant="ghost" className="text-slate-600 font-bold hover:text-blue-600">
                                        Log in
                                    </Button>
                                </Link>
                                <Link to="/register">
                                    <Button className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-6 font-bold shadow-lg shadow-blue-100 transition-all hover:scale-105">
                                        Get Started
                                    </Button>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-24 pb-32 overflow-hidden bg-white">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full pointer-events-none -z-10">
                    <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-50 rounded-full blur-[120px]" />
                    <div className="absolute bottom-[10%] left-[-5%] w-[30%] h-[30%] bg-violet-50 rounded-full blur-[100px]" />
                </div>

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <motion.div
                        initial="initial" animate="animate" variants={stagger}
                        className="text-center max-w-4xl mx-auto"
                    >
                        <motion.div variants={fadeIn} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 border border-blue-100 mb-8">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
                            </span>
                            <span className="text-[10px] font-black text-blue-700 uppercase tracking-widest">Clinical Protocol v2.0 Ready</span>
                        </motion.div>

                        <motion.h1 variants={fadeIn} className="text-5xl md:text-7xl font-black tracking-tight text-slate-900 mb-8 leading-[1.1]">
                            Sepsis Early <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-violet-600">
                                Warning System
                            </span>
                        </motion.h1>

                        <motion.p variants={fadeIn} className="text-lg md:text-xl text-slate-500 mb-12 max-w-2xl mx-auto font-medium leading-relaxed">
                            Advanced real-time risk stratification for intensive care units.
                            Enable proactive intervention with automated clinical triggers.
                        </motion.p>

                        <motion.div variants={fadeIn} className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link to="/login" className="w-full sm:w-auto">
                                <Button size="lg" className="w-full h-14 px-10 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold shadow-xl shadow-blue-100 transition-all hover:scale-105 active:scale-95">
                                    Login
                                    <ArrowRight className="w-5 h-5 ml-2" />
                                </Button>
                            </Link>
                            <Link to="/register" className="w-full sm:w-auto">
                                <Button size="lg" variant="outline" className="w-full h-14 px-10 border-slate-200 text-slate-600 rounded-2xl font-bold hover:bg-slate-50 transition-all">
                                    Register
                                </Button>
                            </Link>
                        </motion.div>
                    </motion.div>

                    {/* Dashboard Preview Visual */}
                    <motion.div
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4, duration: 0.8 }}
                        className="mt-20 relative rounded-[2.5rem] border border-slate-200 bg-slate-50 p-4 shadow-2xl"
                    >
                        <div className="bg-slate-900 rounded-[2rem] overflow-hidden aspect-[21/9] relative group">
                            {/* Medical UI Skeleton */}
                            <div className="absolute inset-0 p-8 grid grid-cols-12 gap-6 opacity-40">
                                <div className="col-span-3 space-y-4">
                                    <div className="h-24 bg-slate-800 rounded-2xl animate-pulse" />
                                    <div className="h-48 bg-slate-800 rounded-2xl animate-pulse" />
                                </div>
                                <div className="col-span-6">
                                    <div className="h-full bg-slate-800 rounded-2xl animate-pulse flex items-center justify-center">
                                        <div className="w-1/2 h-1 bg-blue-600/20 rounded-full" />
                                    </div>
                                </div>
                                <div className="col-span-3 space-y-4">
                                    {[...Array(3)].map((_, i) => (
                                        <div key={i} className="h-20 bg-slate-800 rounded-2xl animate-pulse" />
                                    ))}
                                </div>
                            </div>
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                                <div className="w-16 h-16 bg-blue-600/10 rounded-full flex items-center justify-center animate-bounce">
                                    <Activity className="w-8 h-8 text-blue-500" />
                                </div>
                                <span className="text-slate-400 font-bold tracking-[0.3em] text-xs uppercase">Intelligent Monitoring Active</span>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Feature Grid */}
            <section id="features" className="py-32 bg-slate-50 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-20">
                        <h2 className="text-4xl font-black text-slate-900 mb-4 tracking-tight">Precision Monitoring</h2>
                        <p className="text-slate-500 font-medium max-w-xl mx-auto">
                            Seamless integration into clinical workflows for immediate bed-side impact.
                        </p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={<Zap className="w-6 h-6 text-blue-600" />}
                            title="Real-Time Analysis"
                            description="Continuous processing of multi-parameter vitals with risk scoring powered by validated algorithms."
                        />
                        <FeatureCard
                            icon={<ShieldCheck className="w-6 h-6 text-violet-600" />}
                            title="Clinical Protocol"
                            description="Built-in audit trails and event logging ensure transparency and strict adherence to protocols."
                        />
                        <FeatureCard
                            icon={<BarChart3 className="w-6 h-6 text-blue-600" />}
                            title="Trend Visualization"
                            description="Predictive charts identify physiological deterioration patterns hours before critical events."
                        />
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-24 bg-slate-900 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-[100px]" />
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-violet-600/10 rounded-full blur-[100px]" />

                <div className="max-w-5xl mx-auto px-4 text-center relative z-10">
                    <h2 className="text-4xl md:text-5xl font-black text-white mb-8 tracking-tight">Advance your ICU capabilities.</h2>
                    <p className="text-slate-400 mb-10 text-lg font-medium max-w-2xl mx-auto">
                        Join 50+ leading healthcare institutions using proactive sepsis management to improve survival rates.
                    </p>
                    <Link to="/register">
                        <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 font-black px-12 h-16 rounded-2xl shadow-2xl transition-all hover:scale-105">
                            Create Professional Account
                            <ArrowRight className="w-5 h-5 ml-2" />
                        </Button>
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-white border-t border-slate-200 py-16">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-8">
                    <div className="flex items-center gap-3">
                        <div className="bg-slate-50 p-2 rounded-xl border border-slate-100">
                            <Activity className="w-5 h-5 text-blue-600" />
                        </div>
                        <span className="text-xl font-black text-slate-900 tracking-tighter uppercase">SEWA System</span>
                    </div>
                    <div className="flex gap-8 text-sm font-bold text-slate-400">
                        <a href="#" className="hover:text-blue-600 transition-colors">Privacy</a>
                        <a href="#" className="hover:text-blue-600 transition-colors">Terms</a>
                        <a href="#" className="hover:text-blue-600 transition-colors">Contact</a>
                    </div>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                        © {new Date().getFullYear()} SEWA Medical. HIPAA Compliant.
                    </p>
                </div>
            </footer>
        </div>
    );
}

function FeatureCard({ icon, title, description }) {
    return (
        <motion.div
            whileHover={{ y: -8, scale: 1.02 }}
            className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-slate-200 transition-all hover:shadow-xl group"
        >
            <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mb-8 group-hover:bg-blue-50 transition-colors">
                {icon}
            </div>
            <h3 className="text-xl font-black text-slate-900 mb-4">{title}</h3>
            <p className="text-slate-500 font-medium leading-relaxed text-sm">
                {description}
            </p>
            <div className="mt-6 flex items-center gap-2 text-blue-600 font-bold text-xs uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                Learn more <ChevronRight className="w-4 h-4" />
            </div>
        </motion.div>
    );
}