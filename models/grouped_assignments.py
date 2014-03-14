db.define_table('assignments',
	Field('course',db.courses),
	Field('name', 'string'),
	Field('points', 'integer'),
	Field('grade_type', 'string', default="additive", requires=IS_IN_SET(['additive','checkmark'])),
	Field('threshold', 'integer', default=1),
	format='%(name)s',
	migrate='runestone_assignments.table'
	)

class score(object):
	def __init__(self, acid=None, points=0, comment="", user=None):
		self.acid = acid
		self.user = user
		self.points = points
		self.comment = comment

def assignment_get_scores(assignment, problem=None, user=None, section_id=None):
	scores = []
	if problem and user:
		pass
	elif problem:
		grades = db(db.code.sid == db.auth_user.username)(db.code.acid == problem).select(
			db.code.ALL,
			db.auth_user.ALL,
			orderby = db.code.sid,
			distinct = db.code.sid,
			)
		for g in grades:
			scores.append(score(
				points = g.code.grade,
				acid = g.code.acid,
				user = g.auth_user,
				))
	elif user:
		pass
	else:
		grades = db(db.grades.assignment == assignment.id).select(db.grades.ALL)
		for g in grades:
			scores.append(score(
				points = g.score,
				user = g.auth_user,
				))
	return scores
db.assignments.scores = Field.Method(lambda row, problem=None, user=None, section_id=None: assignment_get_scores(row.assignments, problem, user, section_id))

def assignment_get_problems(assignment, user=None):
	if user:
		q = db(db.problems.acid == db.code.acid)
		q = q(db.problems.assignment == assignment.id)
		q = q(db.code.sid == user.username)
		grades = q.select(
			db.code.acid,
			db.code.grade,
			db.code.comment,
			db.code.timestamp,
			orderby=db.code.acid|db.code.timestamp,
			distinct = db.code.acid,
			)
		# pass back code table in standardized format
		scores = []
		for g in grades:
			s = score(
				acid = g.acid,
				score = 0,
				comment = "",
				user = user,
			)
			s.acid = g.acid # don't know why we need this.
			if g.grade:
				s.score = g.grade
			if g.comment:
				s.comment = g.comment
			scores.append(s)
		return scores
	problems = db(db.problems.assignment == assignment.id).select(
		db.problems.ALL,
		orderby=db.problems.acid
		)
	return problems
def assignment_get_grades(assignment, section_id=None, problem=None):
	""" Return a list of users with grades for assignment (or problem) """
	if section_id:
		section_users = db((db.sections.id==db.section_users.section) & (db.auth_user.id==db.section_users.auth_user))
		users = section_users(db.auth_user.course_id == assignment.course)
		users = users(db.sections.id == section_id)
	else:
		users = db(db.auth_user.course_id == assignment.course)
	users = users.select(
		db.auth_user.ALL,
		orderby = db.auth_user.last_name,
		)
	if problem:
		grades = db(db.code.sid == db.auth_user.username)(db.code.acid == problem).select(
			db.code.ALL,
			db.auth_user.ALL,
			orderby = db.code.sid,
			distinct = db.code.sid,
			)
	else:
		grades = db(db.grades.assignment == assignment.id).select(db.grades.ALL)
	scores = []
	for u in users:
		s = score(
			user = u,
			acid = problem,
			)
		for g in grades:
			if g.auth_user.id == u.id:
				if 'code' in g:
					s.score = g.code.grade
					s.comment = g.code.comment
				elif 'score' in g:
					s.score = g.score
		scores.append(s)
	return scores

def assignment_set_grade(assignment, user):
	# delete the old grades; we're regrading
	db(db.grades.assignment == assignment.id)(db.grades.auth_user == user.id).delete()
	
	points = 0.0
	for prob in assignment.problems(user):
		if not prob.score:
			continue
		points = points + prob.score

	if assignment.grade_type == 'checkmark':
		#threshold grade
		if points >= assignment.threshold:
			points = assignment.points
		else:
			points = 0
	else:
		# they got the points they earned
		pass

	db.grades.insert(
		auth_user = user.id,
		assignment = assignment.id,
		score = points,
		)
	return points
db.assignments.grade = Field.Method(lambda row, user: assignment_set_grade(row.assignments, user))

def assignment_release_grades(assignment, released=True):
	# update problems
	db(db.grades.assignment == assignment.id).update(released=released)
	# update scores
	problems = db(db.problems.assignment == assignment.id).select()
	for problem in problems:
		db(db.scores.acid == problem.acid).update(released = released)
	return True
db.assignments.release_grades = Field.Method(lambda row, released=True: assignment_release_grades(row.assignments, released))

db.define_table('problems',
	Field('assignment',db.assignments),
	Field('acid','string'),
	migrate='runestones_problems.table',
	)

db.define_table('grades',
	Field('auth_user', db.auth_user),
	Field('assignment', db.assignments),
	Field('score', 'double'),
	Field('released','boolean'),
	migrate='runestone_grades.table',
	)

db.define_table('deadlines',
	Field('assignment', db.assignments, requires=IS_IN_DB(db,'assignments.id',db.assignments._format)),
	Field('section', db.sections, requires=IS_EMPTY_OR(IS_IN_DB(db,'sections.id','%(name)s'))),
	Field('deadline','datetime'),
	migrate='runestone_deadlines.table',
	)