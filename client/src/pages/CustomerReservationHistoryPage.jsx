import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Button, Checkbox, DatePicker, Input, InputNumber, Select } from 'antd';
import dayjs from 'dayjs';
import { Link, Navigate, useNavigate } from 'react-router';
import { apiRequest } from '../api/api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { useToast } from '../components/ToastProvider.jsx';

const CHANGE_WINDOW_MS = 48 * 60 * 60 * 1000;

function reservationsFrom(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.reservations)) return response.reservations;
  if (Array.isArray(response?.items)) return response.items;
  return [];
}

function slotsFrom(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.slots)) return response.slots;
  if (Array.isArray(response?.items)) return response.items;
  return [];
}

function formatCreatedAt(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function newestFirst(reservations) {
  return [...reservations].sort((a, b) => {
    const timeA = Date.parse(a.created_at || '');
    const timeB = Date.parse(b.created_at || '');
    const validA = Number.isFinite(timeA);
    const validB = Number.isFinite(timeB);
    if (validA !== validB) return validA ? -1 : 1;
    if (validA) return timeB - timeA;

    const dateA = Date.parse(getReservationDate(a) || '');
    const dateB = Date.parse(getReservationDate(b) || '');
    const validDateA = Number.isFinite(dateA);
    const validDateB = Number.isFinite(dateB);
    if (validDateA !== validDateB) return validDateA ? -1 : 1;
    return validDateA ? dateB - dateA : 0;
  });
}

function slotIdOf(slot) {
  return slot.slot_id ?? slot.slotId ?? slot.id;
}
function slotStartOf(slot) {
  return slot.start_time ?? slot.startTime ?? slot.time ?? '';
}
function slotEndOf(slot) {
  return slot.end_time ?? slot.endTime ?? '';
}
function formatSlotLabel(slot) {
  let label = slotStartOf(slot);
  const end = slotEndOf(slot);
  const mealType = slot.meal_type ?? slot.mealType;
  const name = slot.name ?? slot.label;

  if (end) label += ` – ${end}`;
  if (mealType) label += ` · ${mealType}`;
  else if (name) label += ` · ${name}`;

  return label;
}
function slotPlaceholder(isLoading, availableSlots) {
  if (isLoading) return 'Loading service times…';
  if (availableSlots) return 'Select a time';
  return 'No open times for this date';
}
function isAtLeast48Hours(date, time) {
  const value = Date.parse(`${date}T${String(time).slice(0, 5)}:00`);
  return Number.isFinite(value) && value - Date.now() >= CHANGE_WINDOW_MS;
}

function requirementsFrom(value) {
  if (Array.isArray(value))
    return value.map((item, index) => ({
      id: `${Date.now()}-${index}`,
      has_allergy: Boolean(item?.has_allergy ?? item?.hasAllergy),
      description: String(item?.description ?? ''),
    }));
  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return requirementsFrom(parsed);
    } catch {
      /* Older reservations may store requirements as plain text. */
    }
    return [{ id: `${Date.now()}-0`, has_allergy: false, description: value }];
  }
  return [];
}

function getReservationDate(reservation) {
  return reservation.date ?? reservation.slot?.date ?? reservation.service_date ?? '';
}

function CustomerReservationHistoryPage() {
  const { session } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [target, setTarget] = useState(null);
  const [form, setForm] = useState(null);
  const [slots, setSlots] = useState([]);
  const [slotsDate, setSlotsDate] = useState('');
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const notify = useToast();
  const navigate = useNavigate();

  const loadReservations = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiRequest('/reservations/user', {
        headers: { Authorization: `Bearer ${session.token}` },
      });
      setReservations(newestFirst(reservationsFrom(response)));
    } catch (requestError) {
      if (requestError.status === 404) setReservations([]);
      else notify(requestError.message || 'Could not load your booking history.');
    } finally {
      setLoading(false);
    }
  }, [session, notify]);

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker') return undefined;
    let active = true;
    void Promise.resolve().then(() => {
      if (active) return loadReservations();
      return undefined;
    });
    return () => {
      active = false;
    };
  }, [session, loadReservations]);

  useEffect(() => {
    if (!target || !form?.date) return undefined;
    let active = true;
    apiRequest(`/slots?date=${encodeURIComponent(form.date)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then(async response => {
        const candidates = slotsFrom(response).filter(
          slot => slotIdOf(slot) != null && isAtLeast48Hours(form.date, slotStartOf(slot))
        );
        const checks = await Promise.all(
          candidates.map(async slot => {
            try {
              const availability = await apiRequest(
                `/slots/${encodeURIComponent(slotIdOf(slot))}/availability`,
                {
                  headers: { Authorization: `Bearer ${session.token}` },
                }
              );
              return (availability?.status || '').toUpperCase() === 'OPEN' ? slot : null;
            } catch {
              return null;
            }
          })
        );
        if (active) {
          setSlots(
            checks.filter(Boolean).sort((a, b) => slotStartOf(a).localeCompare(slotStartOf(b)))
          );
          setSlotsDate(form.date);
        }
      })
      .catch(requestError => {
        if (active)
          setError({
            status: requestError.status,
            message: requestError.message || 'Could not load available times.',
          });
      })
      .finally(() => {
        if (active) setSlotsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [target, form?.date, session]);

  const dirty = useMemo(() => {
    if (!target || !form) return false;
    const originalSlot = target.slot_id ?? target.slotId ?? target.slot?.slot_id ?? target.slot?.id;
    const originalDate = getReservationDate(target);
    const originalRequirements = requirementsFrom(target.special_requirements).map(
      ({ has_allergy, description }) => ({ has_allergy, description })
    );
    const currentRequirements = form.requirements.map(({ has_allergy, description }) => ({
      has_allergy,
      description,
    }));
    return (
      String(form.date) !== String(originalDate) ||
      String(form.slot_id) !== String(originalSlot) ||
      Number(form.party_size) !== Number(target.party_size) ||
      JSON.stringify(currentRequirements) !== JSON.stringify(originalRequirements)
    );
  }, [target, form]);

  if (!session?.isAuthenticated || session.userProfile.role !== 'Hiker')
    return <Navigate to="/login" replace />;

  function beginChange(reservation) {
    setTarget(reservation);
    setForm({
      date: getReservationDate(reservation),
      slot_id:
        reservation.slot_id ??
        reservation.slotId ??
        reservation.slot?.slot_id ??
        reservation.slot?.id ??
        null,
      party_size: Number(reservation.party_size) || 1,
      requirements: requirementsFrom(reservation.special_requirements),
    });
    setSlots([]);
    setSlotsDate('');
    setSlotsLoading(true);
    setError(null);
    setFieldErrors({});
  }

  function closeModal() {
    if (submitting) return;
    setTarget(null);
    setForm(null);
    setError(null);
    setFieldErrors({});
  }

  function updateForm(updates) {
    setForm(current => ({ ...current, ...updates }));
    setError(null);
    setFieldErrors({});
  }

  async function handleChangeSubmit(event) {
    event.preventDefault();
    const partySize = Number(form.party_size);
    const validationErrors = {};
    if (!Number.isInteger(partySize) || partySize < 1)
      validationErrors.party_size = 'Party size must be at least 1.';
    if (
      !form.slot_id ||
      slotsDate !== form.date ||
      !slots.some(slot => String(slotIdOf(slot)) === String(form.slot_id))
    ) {
      validationErrors.slot_id = 'Choose an open service time at least 48 hours from now.';
    }
    setFieldErrors(validationErrors);
    if (Object.keys(validationErrors).length) return;

    setSubmitting(true);
    setError(null);
    try {
      await apiRequest(
        `/reservations/reference/${encodeURIComponent(target.booking_reference)}/change`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.token}` },
          body: JSON.stringify({
            slot_id: Number(form.slot_id),
            party_size: partySize,
            special_requirements: form.requirements
              .filter(item => item.description.trim())
              .map(item => ({
                has_allergy: item.has_allergy,
                description: item.description.trim(),
              })),
          }),
        }
      );
      closeModal();
      notify('Booking updated! A confirmation email has been sent.');
      await loadReservations();
    } catch (requestError) {
      if (requestError.status === 401) return;
      if (requestError.status === 403) {
        setError({ status: 403, message: 'You cannot modify this reservation.' });
      } else if (requestError.status === 422) {
        setFieldErrors(requestError.fieldErrors || {});
        setError({
          status: 422,
          message: requestError.message || 'Please check the highlighted fields.',
        });
      } else {
        setError({
          status: requestError.status,
          message: requestError.message || 'The booking could not be changed.',
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page reservation-history-page">
      <header className="reservation-history-header">
        <div>
          <button
            className="back-link"
            type="button"
            onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/home/hiker'))}
          >
            ← Back
          </button>
          <p className="eyebrow">MOUNTAINHUT · YOUR BOOKINGS</p>
          <h1>Booking history</h1>
          <p className="form-intro">Review your reservations and assigned seating.</p>
          <Link className="history-book-button" to="/customer/book-table">
            Book a table
          </Link>
        </div>
        <div className="booking-header-mark" aria-hidden="true">
          MH
        </div>
      </header>
      {loading && <p>Loading your bookings…</p>}
      {!loading && reservations.length === 0 && (
        <p className="reservation-history-empty">You don’t have any bookings yet.</p>
      )}
      {!loading && reservations.length > 0 && (
        <ul className="reservation-history-list">
          {reservations.map((reservation, index) => {
            const date = getReservationDate(reservation);
            const canChange =
              String(reservation.status).toUpperCase() === 'CONFIRMED' &&
              isAtLeast48Hours(
                date,
                reservation.start_time ?? reservation.startTime ?? reservation.slot?.start_time
              );
            return (
              <li
                className={
                  String(reservation.status).toUpperCase() === 'CONFIRMED'
                    ? 'reservation-card-modifiable'
                    : undefined
                }
                key={
                  reservation.reservation_id ?? reservation.reservationId ?? reservation.id ?? index
                }
              >
                <div className="reservation-card-details">
                  <strong>{reservation.booking_reference || 'Booking'}</strong>
                  {date && (
                    <span>
                      {date} · {reservation.start_time ?? reservation.slot?.start_time}–
                      {reservation.end_time ?? reservation.slot?.end_time}
                    </span>
                  )}
                  <span>
                    {reservation.party_size ?? '—'} guests ·{' '}
                    {reservation.status || 'Status unavailable'}
                  </span>
                  {reservation.created_at && (
                    <span>Created {formatCreatedAt(reservation.created_at)}</span>
                  )}
                  {reservation.assigned_tables?.length > 0 && (
                    <span>
                      Tables:{' '}
                      {reservation.assigned_tables
                        .map(
                          table =>
                            `${table.table_number ?? table.tableNumber} (${table.assigned_seats ?? table.assignedSeats} seats)`
                        )
                        .join(', ')}
                    </span>
                  )}
                  {reservation.special_requirements?.length > 0 && (
                    <span>
                      Requests: {reservation.special_requirements.map(item => item.description).join(', ')}
                    </span>
                  )}
                  {(reservation.contact_name || reservation.contact_email) && (
                    <span>
                      Contact:{' '}
                      {[
                        reservation.contact_name,
                        reservation.contact_email,
                        reservation.contact_phone,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  )}
                </div>
                {String(reservation.status).toUpperCase() === 'CONFIRMED' && (
                  <div className="booking-change-action">
                    <Button
                      disabled={!canChange}
                      title={
                        !canChange
                          ? 'Changes are only permitted at least 48 hours in advance.'
                          : undefined
                      }
                      onClick={() => beginChange(reservation)}
                    >
                      Modify booking
                    </Button>
                    {!canChange && (
                      <small>Changes are only permitted at least 48 hours in advance.</small>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {target && form && (
        <div className="change-modal-backdrop">
          <button
            className="change-modal-backdrop-dismiss"
            type="button"
            aria-label="Close modify booking dialog"
            onClick={closeModal}
          />
          <dialog
            open
            className="change-modal"
            aria-modal="true"
            aria-labelledby="change-modal-title"
          >
            <div className="change-modal-heading">
              <div>
                <p className="eyebrow">UPDATE YOUR DETAILS</p>
                <h2 id="change-modal-title">Modify booking</h2>
              </div>
              <button
                className="change-modal-close"
                type="button"
                aria-label="Close"
                onClick={closeModal}
              >
                ×
              </button>
            </div>
            <div className="change-booking-summary">
              <span>
                <strong>Reference</strong>
                {target.booking_reference}
              </span>
              <span>
                <strong>Current tables</strong>
                {target.assigned_tables?.length
                  ? target.assigned_tables
                      .map(
                        table =>
                          `${table.table_number ?? table.tableNumber} (${table.assigned_seats ?? table.assignedSeats} seats)`
                      )
                      .join(', ')
                  : 'Not assigned'}
              </span>
            </div>
            {error && (
              <Alert
                className="change-error-banner"
                type="error"
                showIcon
                title={error.message}
                description={
                  error.status === 409 || error.status === 422
                    ? 'Your original booking remains unchanged.'
                    : undefined
                }
              />
            )}
            <form className="change-modal-form mh-form" onSubmit={handleChangeSubmit}>
              <div className="change-fields">
                <label className="form-field">
                  <span>
                    Date{' '}
                    <span className="required-mark" aria-hidden="true">
                      *
                    </span>
                  </span>
                  <DatePicker
                    className="mh-control"
                    format="YYYY-MM-DD"
                    value={form.date ? dayjs(form.date) : null}
                    disabledDate={date => date.isBefore(dayjs(), 'day')}
                    onChange={value => {
                      setSlots([]);
                      setSlotsDate('');
                      setSlotsLoading(true);
                      updateForm({ date: value?.format('YYYY-MM-DD') || '', slot_id: null });
                    }}
                    allowClear={false}
                    styles={{ popup: { root: { zIndex: 1301 } } }}
                  />
                </label>
                <label className="form-field">
                  <span>
                    Service time{' '}
                    <span className="required-mark" aria-hidden="true">
                      *
                    </span>
                  </span>
                  <Select
                    className="mh-control"
                    value={form.slot_id != null ? String(form.slot_id) : undefined}
                    loading={slotsLoading}
                    disabled={!form.date || slotsDate !== form.date || slots.length === 0}
                    placeholder={slotPlaceholder(slotsLoading, slots.length > 0)}
                    options={slots.map(slot => ({
                      value: String(slotIdOf(slot)),
                      label: formatSlotLabel(slot),
                    }))}
                    onChange={value => updateForm({ slot_id: value })}
                    styles={{ popup: { root: { zIndex: 1301 } } }}
                  />
                  {fieldErrors.slot_id && (
                    <small className="field-error">{fieldErrors.slot_id}</small>
                  )}
                </label>
                <label className="form-field party-size-field">
                  <span>
                    Number of guests{' '}
                    <span className="required-mark" aria-hidden="true">
                      *
                    </span>
                  </span>
                  <InputNumber
                    className="mh-control"
                    min={1}
                    step={1}
                    precision={0}
                    value={form.party_size}
                    onChange={value => updateForm({ party_size: value ?? '' })}
                    aria-invalid={Boolean(fieldErrors.party_size)}
                  />
                  {fieldErrors.party_size && (
                    <small className="field-error">{fieldErrors.party_size}</small>
                  )}
                  <small className="field-hint change-capacity-hint">
                    Changing party size will release current seats and re-assign tables. If capacity
                    is insufficient, your original booking will remain unchanged.
                  </small>
                </label>
                <div className="form-field requirements-field change-requirements-field">
                  <div className="requirements-intro">
                    <span>
                      Special requirements <span className="optional-mark">(optional)</span>
                    </span>
                    <p>
                      Let us know about dietary needs or allergies so we can prepare for your group.
                    </p>
                  </div>
                  {form.requirements.length > 0 && (
                    <div className="requirement-list">
                      {form.requirements.map((requirement, index) => (
                        <article className="requirement-card" key={requirement.id}>
                          <strong className="requirement-index">{index + 1}</strong>
                          <label className="form-field">
                            <span className="sr-only">Requirement {index + 1} description</span>
                            <Input
                              className="mh-control"
                              value={requirement.description}
                              placeholder={
                                index === 0 ? 'e.g. 1 vegan, peanut allergy' : 'e.g. 2 vegetarians'
                              }
                              onChange={event =>
                                updateForm({
                                  requirements: form.requirements.map(item =>
                                    item.id === requirement.id
                                      ? { ...item, description: event.target.value }
                                      : item
                                  ),
                                })
                              }
                            />
                          </label>
                          <Checkbox
                            className="allergy-checkbox"
                            checked={requirement.has_allergy}
                            onChange={event =>
                              updateForm({
                                requirements: form.requirements.map(item =>
                                  item.id === requirement.id
                                    ? { ...item, has_allergy: event.target.checked }
                                    : item
                                ),
                              })
                            }
                          >
                            <span aria-hidden="true">⚠️ </span>This requirement involves an allergy
                          </Checkbox>
                          {form.requirements.length > 1 && (
                            <Button
                              className="requirement-remove"
                              type="text"
                              htmlType="button"
                              aria-label={`Remove requirement ${index + 1}`}
                              onClick={() =>
                                updateForm({
                                  requirements: form.requirements.filter(
                                    item => item.id !== requirement.id
                                  ),
                                })
                              }
                            >
                              Remove
                            </Button>
                          )}
                        </article>
                      ))}
                    </div>
                  )}
                  <Button
                    className="requirement-add"
                    type="dashed"
                    htmlType="button"
                    onClick={() =>
                      updateForm({
                        requirements: [
                          ...form.requirements,
                          {
                            id: `${Date.now()}-${Math.random()}`,
                            has_allergy: false,
                            description: '',
                          },
                        ],
                      })
                    }
                  >
                    ＋ Add requirement
                  </Button>
                  <Checkbox
                    checked={form.requirements.length === 0}
                    onChange={event =>
                      updateForm({
                        requirements: event.target.checked
                          ? []
                          : [{ id: `${Date.now()}`, has_allergy: false, description: '' }],
                      })
                    }
                  >
                    No dietary restrictions or allergies
                  </Checkbox>
                  {fieldErrors.special_requirements && (
                    <small className="field-error">{fieldErrors.special_requirements}</small>
                  )}
                </div>
              </div>
              <footer className="change-modal-actions">
                <Button htmlType="button" onClick={closeModal} disabled={submitting}>
                  Cancel
                </Button>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={submitting}
                  disabled={!dirty || slotsLoading}
                >
                  Save changes
                </Button>
              </footer>
            </form>
          </dialog>
        </div>
      )}
    </main>
  );
}

export default CustomerReservationHistoryPage;
