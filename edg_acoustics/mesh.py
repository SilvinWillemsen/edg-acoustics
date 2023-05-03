"""
``edg_acoustics.mesh``
======================

The edg_acoustics mesh functions and classes provide functionality to process
and access mesh data generated by different mesh generators (e.g.,
`DOLFIN XML <https://manpages.ubuntu.com/manpages/jammy/en/man1/dolfin-convert.1.html>`_ (``.xml``),
`Netgen <https://github.com/ngsolve/netgen>`_ (``.vol``, ``.vol.gz``),
`Gmsh <https://gmsh.info/doc/texinfo/gmsh.html#File-formats>`_ (format versions 2.2, 4.0, and 4.1 ``.msh``)
courtesy of
the `meshio <https://github.com/nschloe/meshio>`_ package.

Please note that the most-used mesh functions and classes in edg_acoustics are present in
the main :mod:`edg_acoustics` namespace rather than in :mod:`edg_acoustics.mesh`.  These are:
:class:`.Mesh`, and :func:`.some_function`.

Functions and classes present in :mod:`edg_acoustics.mesh` are listed below.

Mesh processing
---------------
   Mesh
"""
from __future__ import annotations
import meshio
import numpy


__all__ = ['Mesh']


class Mesh:
    """Mesh data structure generated from common mesh file formats.

    Data structure containing mesh definition. Mesh data is obtained from
    data stored in common mesh file format by
    `Gmsh <https://gmsh.info/doc/texinfo/gmsh.html#File-formats>`_ (format versions 2.2, 4.0, and 4.1 ``.msh``).
    Since mesh reading relies on meshio, other mesh generators can be made available in the future (e.g.,
    `DOLFIN XML <https://manpages.ubuntu.com/manpages/jammy/en/man1/dolfin-convert.1.html>`_ (``.xml``),
    `Netgen <https://github.com/ngsolve/netgen>`_ (``.vol``, ``.vol.gz``).

    :class:`.Mesh` defines the domain discretisation and is used to define
    the finite element approximation of the solution to the acoustic
    wave propagation.

    Args:
        filename (str): the file (pathlike) to read mesh data from. Supported format
            Gmsh (format versions 2.2, 4.0, and 4.1, .msh).
            Since mesh reading relies on meshio, the following formats can be made available in the future:
            Abaqus (.inp), ANSYS msh (.msh), AVS-UCD (.avs), CGNS (.cgns), DOLFIN XML (.xml), Exodus (.e, .exo),
            FLAC3D (.f3grid), H5M (.h5m), Kratos/MDPA (.mdpa), Medit (.mesh, .meshb), MED/Salome (.med),
            Nastran (bulk data, .bdf, .fem, .nas), Netgen (.vol, .vol.gz), Neuroglancer precomputed format,
            Gmsh (format versions 2.2, 4.0, and 4.1, .msh), OBJ (.obj), OFF (.off),
            PERMAS (.post, .post.gz, .dato, .dato.gz), PLY (.ply), STL (.stl), Tecplot .dat, TetGen .node/.ele,
            SVG (2D output only) (.svg), SU2 (.su2), UGRID (.ugrid), VTK (.vtk), VTU (.vtu), WKT (TIN) (.wkt),
            XDMF (.xdmf, .xmf).
        BC_labels (dict[str, int]): a dictionary containing the human readable label of each boundary condition and the
            associated lable number used in the mesh generator. BC_labels['my_label'] returns the label number of the
            label named 'my_label'. If BC_labels['my_label'] is not present in the mesh, an error is raised. If a label
            is present in the mesh but not in BC_labels, an error is raised.

    Raises:
        ValueError: If BC_labels['my_label'] is not present in the mesh, an error is raised. If a label
            is present in the mesh but not in BC_labels, an error is raised.

    Attributes:
        N_vertices (int): The number of vertices that make up the mesh.
        N_tets (int): The number of tetrahedra that make up the mesh (number of elements).
        N_BC_triangles (dict[str, int]): the number of triangles on the boundary of the domain associated to each
            boundary label in self.BC_labels. For example self.N_BC_triangles['my_label'] returns the number of boundary
            triangles associated to lable 'my_label'. 'my_label' must be a key of self.BC_labels.
        vertices (numpy.ndarray): An (self.N_vertices x M) array containing the M coordinates of the self.N_vertices
            vertices that make up the mesh. M specifies the geometric dimension of the mesh, such that the mesh
            describes an M-dimensional domain.
        tets (numpy.ndarray): An (self.N_tets x 4) array containing the 4 indices of the vertices of the self.N_tets
               tetrahedra that make up the mesh.
        BC_triangles (dict[str, numpy.ndarray]):

    Example:
        An element of this class can be initialized in the following way

        >>> import edg_acoustics
        >>> BC_labels = {'slip': 11, 'impedance1': 13, 'impedance2': 14, 'impedance3': 15}
        >>> filename = "../data/tests/mesh/CoarseMesh.msh"
        >>> mesh = edg_acoustics.Mesh(filename, BC_labels)
        <BLANKLINE>
        >>> mesh.N_BC_triangles
        {'slip': 5347, 'impedance1': 400, 'impedance2': 3576, 'impedance3': 3294}

    """

    def __init__(self, filename: str, BC_labels: dict[str, int]):
        # Init from file
        self.__init_from_file(filename, BC_labels)

    def __init_from_file(self, filename: str, BC_labels: dict[str, int]):
        # Load mesh data from mesh file
        mesh_data = meshio.read(filename)

        # Extract the relevant data and store it in the object

        # Read the number of points and their coordinates
        self.N_vertices = mesh_data.points.shape[0]
        self.vertices = mesh_data.points

        # Check if all labels provided as input exist in the mesh data and vice versa, if not, raise error
        BC_labels_in_mesh = sorted(numpy.unique(mesh_data.cell_data_dict['gmsh:physical']['triangle']))  # get labels in the mesh, sort for faster comparison below
        BC_labels_in_input = sorted(BC_labels.values())  # get all labels specified in input
        if not BC_labels_in_input == BC_labels_in_mesh:
            raise ValueError(
                "[edg_acoustics.Mesh] All BC labels must be present in the mesh and all labels in the mesh must be "
                "present in BC_labels.")

        # Read the boundary triangles and their definitions separating them into the different boundary condition labels
        self.N_BC_triangles = {}
        self.BC_triangles = {}
        for BC_label in BC_labels:
            triangles_have_label = (mesh_data.cell_data_dict['gmsh:physical']['triangle'] == BC_labels[BC_label])  # array with bools specifying if triangle has BC_label or not
            self.N_BC_triangles[BC_label] = triangles_have_label.sum()  # number of triangles with label BC_label
            self.BC_triangles[BC_label] = mesh_data.cells_dict['triangle'][triangles_have_label]  # get the triangles with BC_label

        # Read the number of tetrahedra (computational elements) and their definitions
        self.N_tets = mesh_data.cells_dict['tetra'].shape[0]
        self.tets = mesh_data.cells_dict['tetra']

        # Compute the mesh connectivity
        self.EToE, self.EToF = self.__compute_element_connectivity(self.tets)

    # Operators --------------------------------------------------------------------------------------------------------
    def __eq__(self, other):
        if isinstance(other, type(self)):
            # If self and other are mesh objects then check if all properties contain the same data
            are_equal = (self.N_vertices == other.N_vertices
                         and self.N_tets == other.N_tets
                         and self.N_BC_triangles == other.N_BC_triangles
                         and numpy.array_equal(self.vertices, other.vertices)
                         and numpy.array_equal(self.tets, other.tets)
                         and all(numpy.array_equal(item, other.BC_triangles[key]) for key, item in self.BC_triangles.items()))
        else:
            # If they are of different types, then they are not the same
            are_equal = False

        return are_equal

    # ------------------------------------------------------------------------------------------------------------------

    # Static methods ---------------------------------------------------------------------------------------------------
    @staticmethod
    def __compute_element_connectivity(tets: numpy.ndarray):
        """Computes element connectivity.

        Given a mesh made up of N_tets tetrahedra, compute the element connectivity. Element connectivity contains the
        information of the index of the neighbor over each of the four faces of the element and the face index of the
        neighbor shared. This information is returned in two arrays: EToE and EToF.
            EToE: contains the information of which elements are neighbors of an element, i.e., EToE[i, j] returns the
                index of the jth neighbor of element i. The definition of jth neighbor follows the mesh generator's
                convention.
            EToF: contains the information of which face is shared between the element and its neighbor, i.e.,
                EToF[i, j] returns the face index of the jth neighbor of element i. Face indices follow the same
                convention as neighbor indices.

        Args:
            tets (numpy.ndarray): An (N_tets x 4) array containing the 4 indices of the vertices of the N_tets
               tetrahedra that make up the mesh. Another name for this quantity in terms of connectivity relations is
               EToV (the vertices in each element).

        Returns:
            EToE (numpy.ndarray): an (4, N_tets) array containing the information of which elements are neighbors of
                an element, i.e., EToE[j, i] returns the index of the jth neighbor of element i. The definition of jth
                neighbor follows the mesh generator's convention.
            EToF (numpy.ndarray): an (4 x N_tets) array containing the information of which face is shared between the
                element and its neighbor,  i.e.,  EToF[j, i] returns the face index of the jth neighbor of element i.
                Face indices follow the same convention as neighbor indices.
        """

        # Get information on the number of faces, tets, and vertices
        N_faces_per_tet = 4  # number of faces per element
        N_tets = tets.shape[0]  # number of elements in the mesh
        # N_vertices = tets.max() + 1  # number of vertices in the mesh, +1 because indexing starts at 0

        # Create a unique identifier for each face based on the vertices that make up the face
        # the order of the vertices does not matter.

        # This is achieved by first constructing a list with all indices of the vertices of the faces of the elements.
        # This is done face by face:
        #    Face 0: made up of vertices [0, 1, 2]
        #    Face 1: made up of vertices [0, 1, 3]
        #    Face 2: made up of vertices [1, 2, 3]
        #    Face 3: made up of vertices [0, 2, 3]
        face_vertices = numpy.vstack([tets[:, [0, 1, 2]], tets[:, [0, 1, 3]], tets[:, [1, 2, 3]], tets[:, [0, 2, 3]]])

        # Then we sort the indices in each face, so that we can easily identify if two faces are the same by the ordered
        # sequence of nodes
        face_vertices.sort(axis=-1)

        # Construct and array with the index of each face in face_vertices
        face_vertices_idx = numpy.arange(0, N_tets * N_faces_per_tet)

        # EToE must be initialized with (the element index of the element)
        # EToE = [[ 0  1  2 ... (N_tets - 1)]
        #         [ 0  1  2 ... (N_tests - 1)]
        #         [ 0  1  2 ... (N_tests - 1)]
        #         [ 0  1  2 ... (N_tests - 1)]]
        EToE = numpy.arange(0, N_tets).reshape([1, -1]).repeat(repeats=N_faces_per_tet, axis=0)

        # EToF must be initialized with (the face index)
        # EToF = [[  0  0  0  ... 0]       |
        #         [  1  1  1  ... 1]       |> has N_tets columns
        #         [  2  2  2  ... 2]       |
        #         [  3  3  3  ... 3]]      |
        EToF = numpy.arange(0, 4).repeat(repeats=N_tets, axis=0).reshape([-1, N_tets])

        # We now need to uniquely number each set of three faces by their node numbers
        # We could use the old algorithm (here in Matlab form)
        #   id = fnodes(:,1)*Nnodes*Nnodes + fnodes(:,2)*Nnodes+fnodes(:,3)+1;
        # Or we can explicitly use a hash (which is essentially what the old code does). A hash just transforms the
        # three indices that defines all faces into a unique number. Note that we apply the hash to each row
        # (hence the 1).
        face_ids = numpy.apply_along_axis(lambda x: hash(tuple(x)), 1, face_vertices)

        # We now sort the face_ids so that we have the identical faces next to each other
        face_ids_sort_indices = numpy.argsort(face_ids)  # get the ordering that sorts the face_ids
        face_ids = face_ids[face_ids_sort_indices]  # sort the face ids
        face_vertices = face_vertices[face_ids_sort_indices, :]     # reorder the faces so that their corresponding face_ids are sorted
        face_vertices_idx = face_vertices_idx[face_ids_sort_indices]  # reorder the face indices so that their corresponding face_ids are sorted

        # Find the indices of face_ids of all interior faces, i.e., that are shared by two elements
        # i.e., faces that appear twice (one time for each element)
        # Note that these faces appear in pairs (one for each element that shares the face), this index, points to the
        # first face.
        # We wrap numpy.where with numpy.array to get and numpy.array instead of a tuple, we do this because later we
        # need to use these indices and these indices +1, with tuple is not possible. The flatten in the end is to avoid
        # having [[]], which means an extra (unused) dimension in the array.
        interior_face_id_idx = numpy.array(numpy.where(face_ids[0:-1] == face_ids[1:])).flatten()

        # With the indices of face_ids we can compute the indices of the faces associated to the face definition on an
        # element (L) and the neighboring element (R). The interior_faces_face_id_idx corresponds to the indices on the
        # L elements and if we add +1 then we get the index on the R elements.
        # For example, for 2D (for simpler visualization)
        #      ___
        #   |\ \  |
        #   | \ \ |
        #   |__\ \|
        #
        # As can be seen in the figure above, the shared face will appear twice: once for the Left element and another
        # for the Right element. We need to associate the element numbers to each other (EToE) and we need to
        # associate the element number of the element on the left to the face number of the element on the right, and
        # vice versa.
        interior_L_face_vertices_idx = face_vertices_idx[interior_face_id_idx]
        interior_R_face_vertices_idx = face_vertices_idx[interior_face_id_idx + 1]

        # Construct EToE
        # Here we simply associate the R element index to the L element, and then associate the L element index to the
        # R element. Note that here the initialization of EToE plays an important role. We initialized EToE to have
        # the value of the current element for all faces of the element. In this way we can use it on the right-hand
        # side.
        EToE[numpy.unravel_index(numpy.hstack([interior_L_face_vertices_idx, interior_R_face_vertices_idx]), EToE.shape)] = \
            EToE[numpy.unravel_index(numpy.hstack([interior_R_face_vertices_idx, interior_L_face_vertices_idx]), EToE.shape)]

        # Construct EToF
        # The logic is the same as for EToE, the difference is that we now use the initialized EToF on the right-hand
        # side.
        EToF[numpy.unravel_index(numpy.vstack([interior_L_face_vertices_idx, interior_R_face_vertices_idx]), EToF.shape)] = \
            EToF[numpy.unravel_index(numpy.vstack([interior_R_face_vertices_idx, interior_L_face_vertices_idx]), EToF.shape)]

        # Just return EToE and EToF
        return EToE, EToF

    # ------------------------------------------------------------------------------------------------------------------

    # Properties -------------------------------------------------------------------------------------------------------
    @property
    def EToV(self):
        """numpy.ndarray: An (self.N_tets x 4) array containing the 4 indices of the vertices of the self.N_tets
               tetrahedra that make up the mesh. It returns the value in self.tets, since it is the same data."""
        return self.tets
    # ------------------------------------------------------------------------------------------------------------------
