import React, { useState } from 'react'
import axios from 'axios'

function JoinFund() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    investment: '',
    password: ''
  })

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      const response = await axios.post('/api/investor/register', {
        name: formData.name,
        email: formData.email,
        initial_investment: parseFloat(formData.investment),
        kyc_documents: []
      })

      alert('Registration submitted! Status: ' + response.data.status)
    } catch (error) {
      alert('Registration failed: ' + error.message)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold mb-8">Join the Fund</h1>

      <div className="bg-white p-8 rounded-lg shadow">
        {/* Progress Steps */}
        <div className="flex mb-8">
          <div className={`flex-1 text-center pb-2 border-b-2 ${step >= 1 ? 'border-blue-600' : 'border-gray-300'}`}>
            <span className="text-sm">Personal Info</span>
          </div>
          <div className={`flex-1 text-center pb-2 border-b-2 ${step >= 2 ? 'border-blue-600' : 'border-gray-300'}`}>
            <span className="text-sm">Investment Amount</span>
          </div>
          <div className={`flex-1 text-center pb-2 border-b-2 ${step >= 3 ? 'border-blue-600' : 'border-gray-300'}`}>
            <span className="text-sm">Review</span>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold mb-4">Personal Information</h2>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Password</label>
                <input
                  type="password"
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  required
                />
              </div>
              <button
                type="button"
                onClick={() => setStep(2)}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
              >
                Next
              </button>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-xl font-bold mb-4">Investment Amount</h2>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Initial Investment (USD)</label>
                <input
                  type="number"
                  min="1000"
                  step="100"
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                  value={formData.investment}
                  onChange={(e) => setFormData({...formData, investment: e.target.value})}
                  required
                />
                <p className="text-sm text-gray-500 mt-1">Minimum investment: $1,000</p>
              </div>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="bg-gray-300 text-gray-700 px-6 py-2 rounded-md hover:bg-gray-400"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-xl font-bold mb-4">Review & Submit</h2>
              <div className="bg-gray-50 p-4 rounded-md mb-4">
                <p><strong>Name:</strong> {formData.name}</p>
                <p><strong>Email:</strong> {formData.email}</p>
                <p><strong>Investment:</strong> ${parseFloat(formData.investment).toLocaleString()}</p>
              </div>
              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="bg-gray-300 text-gray-700 px-6 py-2 rounded-md hover:bg-gray-400"
                >
                  Back
                </button>
                <button
                  type="submit"
                  className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700"
                >
                  Submit Application
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}

export default JoinFund
