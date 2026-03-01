import React, { useState } from 'react';
import { useChatStore } from '../store';
import { interviewAPI } from '../api';

export function Results() {
  const top3Candidates = useChatStore((state) => state.top3Candidates);
  const currentJob = useChatStore((state) => state.currentJob);
  const [selectedCandidates, setSelectedCandidates] = useState([]);
  const [googleMeetLink, setGoogleMeetLink] = useState('');
  const [inviteSent, setInviteSent] = useState(false);
  const [loading, setLoading] = useState(false);
  
  if (!top3Candidates || top3Candidates.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>No candidates matched yet. Analyze a job description first.</p>
      </div>
    );
  }
  
  const handleSelectCandidate = (resumeId) => {
    setSelectedCandidates((prev) =>
      prev.includes(resumeId)
        ? prev.filter((id) => id !== resumeId)
        : [...prev, resumeId]
    );
  };
  
  const handleSendInvite = async () => {
    setLoading(true);
    try {
      // Get email addresses from selected candidates
      const candidateEmails = top3Candidates
        .filter((c) => selectedCandidates.includes(c.resume_id))
        .map((c) => c.candidate_name); // In real app, would use actual emails from metadata
      
      await interviewAPI.sendInvite(
        candidateEmails,
        googleMeetLink,
        currentJob?.job_id
      );
      
      setInviteSent(true);
      setTimeout(() => setInviteSent(false), 3000);
    } catch (error) {
      console.error('Error sending invite:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold">Top 3 Candidates</h2>
      
      {/* Candidates Cards */}
      <div className="grid gap-4">
        {top3Candidates.map((candidate, idx) => (
          <div
            key={candidate.resume_id}
            className="border border-gray-300 rounded-lg p-4 bg-white hover:shadow-lg transition"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold">
                  #{candidate.rank} - {candidate.candidate_name}
                </h3>
                <p className="text-gray-600 text-sm">{candidate.source_file}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-green-600">
                  {candidate.alignment_score}%
                </p>
                <p className="text-sm text-gray-600">
                  Confidence: {candidate.confidence}
                </p>
              </div>
            </div>
            
            {/* Skills Met */}
            <div className="mb-4">
              <p className="font-semibold text-green-700 text-sm mb-2">✓ Skills Met:</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {candidate.required_skills_met.map((skill, i) => (
                  <span
                    key={i}
                    className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-xs"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            
            {/* Skills Missing */}
            {candidate.required_skills_missing.length > 0 && (
              <div className="mb-4">
                <p className="font-semibold text-red-700 text-sm mb-2">✗ Skills Missing:</p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {candidate.required_skills_missing.map((skill, i) => (
                    <span
                      key={i}
                      className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-xs"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* Reasoning */}
            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
              <p className="text-sm font-semibold text-gray-700 mb-2">Reasoning:</p>
              <p className="text-sm text-gray-600">{candidate.reasoning}</p>
            </div>
            
            {/* Selection Checkbox */}
            <div className="mt-4 flex items-center">
              <input
                type="checkbox"
                checked={selectedCandidates.includes(candidate.resume_id)}
                onChange={() => handleSelectCandidate(candidate.resume_id)}
                className="w-4 h-4 text-blue-600 rounded cursor-pointer"
              />
              <label className="ml-2 text-sm font-medium text-gray-700 cursor-pointer">
                Send Interview Invite
              </label>
            </div>
          </div>
        ))}
      </div>
      
      {/* Interview Invitation Section */}
      {selectedCandidates.length > 0 && (
        <div className="bg-blue-50 border border-blue-300 rounded-lg p-6 mt-6">
          <h3 className="text-lg font-bold mb-4">Send Interview Invitations</h3>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Google Meet Link
            </label>
            <input
              type="url"
              placeholder="https://meet.google.com/xxx-xxxx-xxx"
              value={googleMeetLink}
              onChange={(e) => setGoogleMeetLink(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <p className="text-sm text-gray-600 mb-4">
            Inviting {selectedCandidates.length} candidate(s)
          </p>
          
          <button
            onClick={handleSendInvite}
            disabled={loading || !googleMeetLink}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg transition disabled:opacity-50"
          >
            {loading ? 'Sending...' : 'Send Interview Invites'}
          </button>
          
          {inviteSent && (
            <p className="text-green-600 text-sm mt-2">✓ Invitations sent successfully!</p>
          )}
        </div>
      )}
    </div>
  );
}
