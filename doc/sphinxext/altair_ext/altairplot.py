"""Altair Directive for sphinx"""

import ast
import os
import json

import jinja2

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import flag, unchanged

from sphinx.locale import _
from sphinx import addnodes, directives
from sphinx.util.nodes import set_source_info

try:
    import altair
    from altair.api import TopLevelMixin
except ImportError:
    altair = None


VGL_TEMPLATE = jinja2.Template("""
<div id="{{ div_id }}">
<script src="https://d3js.org/d3.v3.min.js"></script>
<script src="https://vega.github.io/vega/vega.js"></script>
<script src="https://vega.github.io/vega-lite/vega-lite.js"></script>
<script src="https://vega.github.io/vega-editor/vendor/vega-embed.js" charset="utf-8"></script>
<script>
  vg.embed("#{{ div_id }}", "{{ filename }}", function(error, result) {});
</script>
</div>
""")


def exec_then_eval(code):
    """Exec a code block & return evaluation of the last line"""
    block = ast.parse(code, mode='exec')
    last = ast.Expression(block.body.pop().value)

    globals = {}
    locals = {}
    exec(compile(block, '<string>', mode='exec'), globals, locals)
    return eval(compile(last, '<string>', mode='eval'), globals, locals)


class altair_plot(nodes.General, nodes.Element):
    pass


class AltairPlotDirective(Directive):

    has_content = True

    option_spec = {'show-json': flag,
                   'hide-code': flag,
                   'code-below': flag,
                   'alt': unchanged}

    def run(self):
        env = self.state.document.settings.env
        app = env.app

        show_code = 'hide-code' not in self.options
        show_json = 'show-json' in self.options
        code_below = 'code-below' in self.options

        code = '\n'.join(self.content)
        chart = exec_then_eval(code)
        spec = chart.to_dict()

        if show_code:
            source_literal = nodes.literal_block(code, code)
            source_literal['language'] = 'python'

        if show_json:
            spec_json = json.dumps(spec, indent=2)
            json_literal = nodes.literal_block(specjson, specjson)
            json_literal['language'] = 'json'

        #get the name of the source file we are currently processing
        rst_source = self.state_machine.document['source']
        rst_dir = os.path.dirname(rst_source)
        rst_filename = os.path.basename(rst_source)
        rst_base = rst_filename.replace('.', '-')

        # use the source file name to construct a friendly target_id
        serialno = env.new_serialno('altair-plot')
        target_id = "{0}-altair-source-{1}".format(rst_base, serialno)
        div_id = "{0}-altair-plot-{1}".format(rst_base, serialno)
        target_node = nodes.target('', '', ids=[target_id])

        # this is the node in which the plot will appear
        plot_node = altair_plot()
        plot_node['target_id'] = target_id
        plot_node['div_id'] = div_id
        plot_node['source'] = source_literal
        plot_node['relpath'] = os.path.relpath(rst_dir, env.srcdir)
        plot_node['rst_source'] = rst_source
        plot_node['rst_lineno'] = self.lineno
        plot_node['spec'] = spec

        if 'alt' in self.options:
            plot_node['alt'] = self.options['alt']

        result = [target_node]

        if code_below:
            result += [plot_node]
        if show_code:
            result += [source_literal]
        if show_json:
            result += [json_literal]
        if not code_below:
            result += [plot_node]

        return result


def html_visit_altair_plot(self, node):
    # Create the vega-lite spec to embed
    embed_spec = json.dumps({'mode': 'vega-lite',
                             'spec': node['spec']})

    # Write embed_spec to a *.vl.json file
    dest_dir = os.path.join(self.builder.outdir, node['relpath'])
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    filename = "{0}.vl.json".format(node['div_id'])
    dest_path = os.path.join(dest_dir, filename)
    with open(dest_path, 'w') as f:
        f.write(embed_spec)

    # Create a template that will render this file
    html = VGL_TEMPLATE.render(div_id=node['div_id'],
                               filename=filename)
    self.body.append(html)
    raise nodes.SkipNode


def generic_visit_altair_plot(self, node):
    if 'alt' in node.attributes:
        self.body.append(_('[ graph: %s ]') % node['alt'])
    else:
        self.body.append(_('[ graph ]'))
    raise nodes.SkipNode


latex_visit_altair_plot = generic_visit_altair_plot
texinfo_visit_altair_plot = generic_visit_altair_plot
text_visit_altair_plot = generic_visit_altair_plot
man_visit_altair_plot = generic_visit_altair_plot


def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir

    app.add_node(altair_plot,
                 html=(html_visit_altair_plot, None),
                 latex=(latex_visit_altair_plot, None),
                 texinfo=(texinfo_visit_altair_plot, None),
                 text=(text_visit_altair_plot, None),
                 man=(man_visit_altair_plot, None))

    app.add_directive('altair-plot', AltairPlotDirective)

    return {'version': '0.1'}
